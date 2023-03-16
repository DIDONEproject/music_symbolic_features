from dataclasses import dataclass

import ipdb
import autosklearn.metrics
import plotly.express as px
from autosklearn.classification import AutoSklearnClassifier
from sklearn.dummy import DummyClassifier
from sklearn.model_selection import StratifiedKFold, cross_validate

from . import settings as S
from .data import TASKS, Task
from .utils import AbstractMain, logger, plotly_save


def random_guessing(task, splitter):
    # Define a dictionary with the different strategies to try
    strategies = {
        "most_frequent": DummyClassifier(strategy="most_frequent"),
        "stratified": DummyClassifier(strategy="stratified"),
        "uniform": DummyClassifier(strategy="uniform"),
    }

    if splitter is None:
        splitter = 5

    # Initialize a dictionary to store the results for each strategy
    results = {}

    # Loop through each strategy
    for strategy_name, strategy in strategies.items():
        # Use cross_validate to get the scores for the strategy
        scores = cross_validate(
            estimator=strategy,
            X=task.x,
            y=task.y,
            cv=splitter,
            scoring=["balanced_accuracy"],
            return_train_score=False,
        )

        # Add the mean score for the strategy to the results dictionary
        results[strategy_name] = scores["test_balanced_accuracy"].mean()
    return max(results.values())


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
    if task.extension != ".mid":
        return
    logger.info(f"Starting AutoML on {task.name}")
    if S.DEBUG:
        smac_scenario_args = None # {"runcount_limit": 2}
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
    dataset_key = task.dataset.friendly_name + "-" + task.extension
    if dataset_key in performances:
        performances[dataset_key][task.feature_set.name] = pot_copy
    else:
        performances[dataset_key] = {}
        performances[dataset_key][task.feature_set.name] = pot_copy


@dataclass
class Main(AbstractMain):
    debug: bool = False

    def classification(self):
        if self.debug:
            print("press C to continue ")
            __import__("ipdb").set_trace()
        splitter = StratifiedKFold(S.SPLITS)

        performances = {}
        for task in TASKS:
            pot = automl(task, splitter, S.AUTOML_TIME, output=task.name + ".csv")
            if pot is None:
                continue
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

            fig = px.line()

            for name, df in dfs.items():
                fig.add_scatter(
                    x=df["Timestamp"], y=df["ensemble_optimization_score"], name=name
                )
            fig.update_layout(
                title=plot_name,
                xaxis_title="Time",
                yaxis_title=f"Avg {S.SPLITS}-fold Balanced Accuracy",
                xaxis_tickformat="%H:%M",
            )
            plotly_save(fig, plot_name + ".svg")


if __name__ == "__main__":
    import fire

    fire.Fire(Main)
