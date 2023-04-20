import os
import datetime
from dataclasses import dataclass

import autosklearn.metrics
import numpy as np
import plotly.express as px
from autosklearn.classification import AutoSklearnClassifier
from joblib import Parallel, delayed
from rich.progress import track
from sklearn.dummy import DummyClassifier
from sklearn.model_selection import StratifiedKFold, cross_validate

from . import settings as S
from .data import Task, load_tasks
from .utils import AbstractMain, logger, plotly_save


def random_guessing(task, splitter):
    """
    Run each of the dummy strategies a given number of times and return the
    maximum value.
    """
    strategies = ["most_frequent", "stratified", "uniform"]

    if splitter is None:
        splitter = 5

    def compute_scores(idx, strategy_name, task, splitter):
        strategy = DummyClassifier(strategy=strategy_name, random_state=idx)
        scores = cross_validate(
            estimator=strategy,
            X=task.x,
            y=task.y,
            cv=splitter,
            scoring=["balanced_accuracy"],
            return_train_score=False,
        )
        return strategy_name, scores["test_balanced_accuracy"].mean()

    scores = Parallel(n_jobs=-1)(
        delayed(compute_scores)(idx, strategy_name, task, splitter)
        for strategy_name, idx in track(
            zip(
                strategies * S.DUMMY_TRIALS,
                range(len(strategies * S.DUMMY_TRIALS)),
            ),
            description="Dummy strategies",
        )
    )

    scores = [np.mean([v for k_, v in scores if k_ == k]) for k in strategies]

    return max(scores)


def plot_time_performance(performance_data, fname=None):
    """
    Plot the performance over time of the best mdels in automl_data
    You can use `easy_tools.get_automl` to load the most recent `automl_data`.
    """
    fig = px.line(
        performance_data,
        x="Timestamp",
        y=performance_data,
    )
    if fname:
        plotly_save(fig, fname)
    return fig


def automl(task: Task, splitter=None, automl_time=3600, output=None):
    """
    Apply AutoSklearn to a task and saves csv of the optimization if output is not
    None
    """
    logger.info("------------------------------")
    logger.info("------------------------------")
    logger.info(f"Starting AutoML on {task.name}")
    if S.DEBUG:
        smac_scenario_args = None  # {"runcount_limit": 2}
        metalearning = 25
        automl_time = 300
    else:
        smac_scenario_args = None
        metalearning = 25

    task.load_csv()
    logger.info(f"Shape of the X dataframe: {task.x.shape}")
    logger.info(f"Number of labels in y: {task.y.unique().shape}")

    assert task.x.shape[0] > 2 * S.SPLITS, "Not enough data in x"
    assert task.x.shape[0] == task.y.shape[0], "X and y have different shapes"
    random_guess = random_guessing(task, splitter)
    logger.info(f"Random Guessing: {random_guess}")

    classifier = AutoSklearnClassifier(
        seed=1993,
        time_left_for_this_task=automl_time,
        initial_configurations_via_metalearning=metalearning,
        smac_scenario_args=smac_scenario_args,
        n_jobs=-1,
        memory_limit=10000,
        ensemble_nbest=10,
        metric=autosklearn.metrics.balanced_accuracy,
        resampling_strategy=splitter,
    )
    classifier.fit(task.x, task.y)

    acc = classifier.performance_over_time_["ensemble_optimization_score"].max()
    logger.info(f"Balanced accuracy: {acc:.2e}")
    if output is not None:
        classifier.performance_over_time_.to_csv(output)

    return classifier.performance_over_time_


def add_task_result(performances, pot, task):
    """
    Add the result of an automl (pot=performance_over_time_) to the dict `performences`
    """
    # select columns
    pot = pot[["Timestamp", "ensemble_optimization_score"]]
    # time start from 0
    pot_copy = pot.copy()  # to avoid pandas warnings...
    pot_copy["Timestamp"] = pot["Timestamp"] - pot["Timestamp"].min()
    # store data
    dataset_key = task.dataset.friendly_name + "-" + task.extension[1:]  # no dot
    if dataset_key in performances:
        performances[dataset_key][task.feature_set.name] = pot_copy
    else:
        performances[dataset_key] = {}
        performances[dataset_key][task.feature_set.name] = pot_copy


@dataclass
class Main(AbstractMain):
    debug: bool = False
    keep_first_10_pc: bool = False
    automl_time: int = 1800

    def classification(
        self, featureset: str = None, dataset: str = None, extension: str = None
    ):
        if self.debug:
            print("press C to continue ")
            __import__("ipdb").set_trace()
        splitter = StratifiedKFold(S.SPLITS, random_state=42, shuffle=True)

        for task in load_tasks():
            # skipping tasks not matching the filters
            if featureset is not None and featureset != task.name:
                continue
            if dataset is not None and dataset != task.name:
                continue
            if extension is not None and extension not in task.name:
                continue
            if os.path.exists(task.name + ".csv"):
                logger.info(f"Skipping {task.name}, already done")
                continue
            automl(task, splitter, S.AUTOML_TIME, output=task.name + ".csv")

    def plot_performances(self):
        import pandas as pd

        performances = {}
        for task in load_tasks():
            try:
                pot = pd.read_csv(task.name + ".csv")
            except FileNotFoundError:
                logger.warning(f"File {task.name}.csv not found")

            try:
                pot["Timestamp"] = pd.to_datetime(pot["Timestamp"])
            except Exception as e:
                logger.warning(f"Error converting Timestamp to datetime: {e}")
            add_task_result(performances, pot, task)

        # plotting the performances over time
        for plot_name, dfs in performances.items():
            # Resample the data to a common frequency (every minute)
            for k in dfs:
                dfs[k] = (
                    dfs[k]
                    .set_index("Timestamp")
                    .resample("100ms", closed="right")
                    .max()
                    .ffill()
                    .reset_index()
                )

            for k in dfs:
                dfs[k]["Timestamp"] = (
                    dfs[k]["Timestamp"]
                    .dt.total_seconds()
                    .astype(int)
                    .apply(lambda x: str(datetime.timedelta(seconds=x)))
                )

            fig = px.line()

            for name, df in dfs.items():
                fig.add_scatter(
                    x=df["Timestamp"],
                    y=1 - df["ensemble_optimization_score"],
                    name=name,
                )
            fig.update_layout(
                title=plot_name,
                xaxis_title="Time",
                yaxis_title=f"Avg {S.SPLITS}-fold Mean Per Class Error",
                xaxis_tickformat="H:M",
                yaxis_type="log",
            )
            plotly_save(fig, plot_name + ".svg")


if __name__ == "__main__":
    import fire

    fire.Fire(Main)
