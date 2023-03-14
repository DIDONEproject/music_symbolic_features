from dataclasses import dataclass

import autosklearn.metrics
import plotly.express as px
from autosklearn.classification import AutoSklearnClassifier
from sklearn.model_selection import StratifiedKFold

from . import settings as S
from .data import TASKS, Task
from .utils import AbstractMain, logger, plotly_save


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
    logger.info(f"Starting AutoML on {task.name}")
    if S.DEBUG:
        smac_scenario_args = {"runcount_limit": 2}
        metalearning = 0
        automl_time = 30
    else:
        smac_scenario_args = None
        metalearning = 25

    task.load_csv()

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
    assert task.x.shape[0] > S.SPLITS, "Not enough data in x"
    assert task.x.shape[0] == task.y.shape[0], "X and y have different shapes"
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
    pot["Timestamp"] = pot["Timestamp"] - pot["Timestamp"].min()
    # store data
    dataset_key = task.dataset.friendly_name + "-" + task.extension
    if dataset_key in performances:
        performances[dataset_key].append(pot)
    else:
        performances[dataset_key] = [pot]


@dataclass
class Main(AbstractMain):
    debug: bool = False

    def classification(self):
        if self.debug:
            print("press C to continue ")
            # __import__('ipdb').set_trace()
        splitter = StratifiedKFold(S.SPLITS)

        performances = {}
        for task in TASKS:
            try:
                pot = automl(task, splitter, S.AUTOML_TIME, output=task.name + ".csv")
            except Exception as e:
                import traceback
                trace = traceback.extract_tb(e.__traceback__)
                line = trace[-1]
                filename, line_num, func_name, code = line
                logger.error(e)
                logger.error(f"{filename}:{line_num} - {code.strip()}")
                continue
            add_task_result(performances, pot, task)

        # plotting the performances over time
        for plot_name, dfs in performances.items():
            # Resample the data to a common frequency (every minute)
            for i in range(len(dfs)):
                dfs[i] = (
                    dfs[i]
                    .set_index("Timestamp")
                    .resample("1min")
                    .asfreq()
                    .reset_index()
                )

            fig = px.line()

            for df in dfs:
                fig.add_scatter(x=df["Timestamp"], y=df["Score"])
            plotly_save(fig, plot_name + '.svg')


if __name__ == "__main__":
    import fire

    fire.Fire(Main)
