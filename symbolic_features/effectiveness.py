import autosklearn.metrics
import plotly.express as px
from autosklearn import AutoSklearnClassifier
from sklearn.validation import StratifiedKFold

from . import settings as S
from .data import TASKS, Task
from .utils import logger, plotly_save


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
    classifier = AutoSklearnClassifier(
        cv=splitter,
        seed=1993,
        time_left_for_this_task=automl_time,
        n_jobs=-1,
        memory_limit=10000,
        ensemble_nbest=10,
        metric=autosklearn.metrics.balanced_accuracy,
        resampling_strategy=splitter,
    )
    classifier.fit(task.x, task.y)

    __import__('ipdb').set_trace()
    acc = classifier.performance_over_time_["ensmble_test_score"].max()
    logger.info(f"Balanced accuracy: {acc:.2e}")
    if output is not None:
        classifier.performance_over_time_.to_csv(output)

    return classifier.performance_over_time_


def classification():
    splitter = StratifiedKFold(S.SPLITS)

    for task in TASKS:
        automl(task, splitter, S.AUTOML_TIME)
        # TODO: collect performenaces over time and plot them dataset by dataset
