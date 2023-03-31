import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Tuple, Union

import chardet
import music21
import numpy as np
import pandas as pd
from rich.progress import track
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from . import settings as S
from .utils import logger

__all_exts__ = (".mid", ".xml", ".musicxml", ".mxl", ".krn")


def filter_music21_features(
    df: pd.DataFrame, feature_type: str = "both"
) -> pd.DataFrame:
    """
    Filters the given DataFrame to remove columns that correspond to the specified
    feature type.

    Parameters:
    df (pd.DataFrame): The DataFrame to filter.
    feature_type (str): The type of feature to filter. Can be "both", "native", or
    "jSymbolic". Defaults to "both".

    Returns:
    pd.DataFrame: The filtered DataFrame.

    Raises:
    TypeError: If the input DataFrame is not a pandas DataFrame.
    ValueError: If the feature_type parameter is not one of "both", "pitch", or "rhythm".
    """
    feature_ids = get_music21_features_ids(feature_type)
    filtered_cols = [
        col
        for col in df.columns
        if not any(col.startswith(feature_id) for feature_id in feature_ids)
    ]
    return df[filtered_cols]


def get_music21_features_ids(feature_type="both"):
    """
    Returns the list of features extracted by music21's module (IDs). It iterates all
    the classes found in the music21.features.jSymbolic.featureExtractors or
    music21.features.native.featureExtractors object (a list of classes) and returns a
    list containing the static `id` field of each class.

    Args:
    - feature_type (str): A string representing the type of features to extract. Possible
    values are 'jSymbolic', 'native', or 'both'. Default is 'both'.

    Returns:
    - features (list): A list of strings representing the IDs of the features extracted
    by music21's module.
    """
    features = []
    if feature_type == "jSymbolic":
        feature_classes = music21.features.jSymbolic.featureExtractors
    elif feature_type == "native":
        feature_classes = music21.features.native.featureExtractors
    else:
        feature_classes = (
            music21.features.jSymbolic.featureExtractors
            + music21.features.native.featureExtractors
        )
    for feature_class in feature_classes:
        features.append(feature_class.id)
    return features


@dataclass
class FeatureSet:
    """
    A class representing a set of features for a dataset.

    Attributes:
    -----------
    name : str
        The name of the feature set.
    filename_col : str
        The column used for the filename.
    label_col_selector : Union[List[str], str]
        The column used for extracting labels.
    illegal_cols : List[str]
        A list of columns to be removed from the dataset.
    accepted_exts : Tuple[str]
        A tuple of accepted file extensions.
    music21_filter : Optional[str]
        A string with possible values `both`, `native` and `jSymbolic`. Defaults to
        None, so no filtering is applied.

    Methods:
    --------
    parse(df: pd.DataFrame) -> pd.DataFrame:
        Removes the illegal columns from the given dataframe.

    accepts(ext: str) -> bool:
        Returns True if the given file extension is accepted, False otherwise.
    """

    name: str
    filename_col: str
    label_col_selector: Union[List[str], str]
    illegal_cols: List[str]
    accepted_exts: Tuple[str]
    music21_filter: Optional[str] = None
    csvname: Optional[str] = None

    def __post_init__(self):
        if self.csvname is None:
            self.csvname = self.name

    def parse(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Removes the illegal columns from the given dataframe.

        Parameters:
        -----------
        df : pd.DataFrame
            The dataframe to be parsed.

        Returns:
        --------
        pd.DataFrame
            The parsed dataframe.
        """
        if len(self.illegal_cols) > 0:
            df = df.drop(columns=self.illegal_cols)
        if self.music21_filter is not None:
            df = filter_music21_features(df, self.music21_filter)
        return df

    def accepts(self, ext: str) -> bool:
        """
        Returns True if the given file extension is accepted, False otherwise.

        Parameters:
        -----------
        ext : str
            The file extension to be checked.

        Returns:
        --------
        bool
            True if the file extension is accepted, False otherwise.
        """
        return ext in self.accepted_exts


feature_sets = [
    FeatureSet("musif", "FileName", "FileName", ["Id", "WindowId"], __all_exts__),
    FeatureSet(
        "musif_native",
        "FileName",
        "FileName",
        ["Id", "WindowId"],
        __all_exts__,
        music21_filter="all",
        csvname="musif",
    ),
    FeatureSet("music21", "FileName_0", "FileName_0", [], __all_exts__),
    FeatureSet(
        "music21_native",
        "FileName_0",
        "FileName_0",
        [],
        __all_exts__,
        music21_filter="native",
        csvname="music21",
    ),
    # FeatureSet(
    #     "music21_jSymbolic",
    #     "FileName_0",
    #     "FileName_0",
    #     [],
    #     __all_exts__,
    #     music21_filter="jSymbolic",
    # ),
    FeatureSet("jsymbolic", "Unnamed: 0", "Unnamed: 0", [], [".mid"]),
]


@dataclass
class Dataset:
    name: str
    make_label: Callable[[pd.DataFrame, str], pd.Series]
    label_content: str
    extensions: List[str]
    legal_filenames: str = r".*"
    friendly_name: str = None
    nsplits: int = S.SPLITS

    def __post_init__(self):
        if self.friendly_name is None:
            self.friendly_name = self.name

    def parse(
        self,
        df: pd.DataFrame,
        filename_col: str,
        label_col_selector: str,
        remove_col_label: bool = True,
    ) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
        """
        Parses a dataframe by removing unwanted rows, creating label, and removing label
        column. If nsplits is not None (default) only classes with cardinality >
        2*nsplits are retained.

        Parameters:
        -----------
        df : pd.DataFrame
            The input dataframe to be parsed.
        filename_col : str
            The name of the column containing the filenames.
        label_col_selector : str
            The name of the column containing the labels.
        remove_col_label : bool, optional
            Whether to remove the label column or not. Default is True.

        Returns:
        --------
        Tuple[pd.DataFrame, pd.Series, pd.Series]
            Returns a tuple containing the parsed dataframe, the labels, and the filenames.
        """
        df, y = self.make_label(df, label_col_selector)

        # removing invalid rows
        idx = df[label_col_selector].str.fullmatch(self.legal_filenames).to_numpy()
        df = df.loc[idx]
        y = y.loc[idx]
        # removing classes with little cardinality
        if self.nsplits is not None:
            y_vals, y_freq = np.unique(y, return_counts=True)
            y_vals = y_vals[y_freq > self.nsplits]
            idx = y.isin(y_vals).to_numpy()
            y = y.loc[idx]
            df = df.loc[idx]

        filenames = df[filename_col]
        if remove_col_label is not None:
            df = df.drop(columns=label_col_selector)
        dataset_path = str(S.DATASETS[self.name])
        filenames = filenames.str.replace(f".*{dataset_path}/?", "", regex=True)
        return df, y, filenames


def asap_label(df: pd.DataFrame, label_col_selector: str):
    y = df[label_col_selector].str.extract(r".*asap-dataset/(\w+)/.*", expand=False)
    assert not y.isna().any(), "asap: NaN in y!"
    return df, y


def didone_label(df: pd.DataFrame, label_col_selector: str):
    y = df[label_col_selector].str.extract(
        r".*/xml/[\w -]+-1(\d{2})\d-[\w\[\]-]+", expand=False
    )
    y = y.replace("97", "79")
    y = y.fillna("nd")
    assert not y.isna().any(), "Didone: NaN in y!"
    return df, y


def ewld_label(df: pd.DataFrame, label_col_selector: str):
    conn = sqlite3.connect(S.DATASETS["EWLD"] / "EWLD.db")

    # thanks ChatGPT
    query = """
    SELECT works.path_leadsheet, work_genres.genre
    FROM works
    JOIN work_genres ON works.id = work_genres.id
    GROUP BY works.id
    HAVING MAX(work_genres.occurrences) = work_genres.occurrences;
    """

    # execute the SQL query and convert the result to a Pandas DataFrame
    db_df = pd.read_sql_query(query, conn)

    # removing path to the EWLD dataset
    df[label_col_selector] = df[label_col_selector].str.replace(
        rf".*{S.DATASETS['EWLD']}/", "", regex=True
    )
    # removing extension
    df[label_col_selector] = df[label_col_selector].str[:-4]
    db_df["path_leadsheet"] = db_df["path_leadsheet"].str[:-4]

    # replacing strange characters
    db_df["path_leadsheet"] = db_df["path_leadsheet"].str.replace(",", "_")
    db_df["path_leadsheet"] = db_df["path_leadsheet"].str.replace(";", "_")
    db_df["path_leadsheet"] = db_df["path_leadsheet"].str.replace(" ", "_")

    # remove duplicates
    db_df = db_df.groupby("path_leadsheet").first().reset_index()

    # select the rows in the DataFrame that match the database rows
    idx = df[label_col_selector].isin(db_df["path_leadsheet"])
    df = df[idx]

    y = db_df["genre"]
    idx = db_df["path_leadsheet"].isin(df[label_col_selector])
    y = y[idx]
    y.index = df.index
    assert not y.isna().any(), "EWLD: NaN in y!"
    return df, y


def jlr_label(df: pd.DataFrame, label_col_selector: str):
    y = df[label_col_selector].str.extract(
        r".*mass-duos-corpus-josquin-larue/([\s\w\(\)]+)/.*", expand=False
    )
    assert not y.isna().any(), "JLR: NaN in y!"
    return df, y


def quartets_label(df: pd.DataFrame, label_col_selector: str):
    y = df[label_col_selector].str.extract(r".*quartets/(\w+)/.*", expand=False)
    assert not y.isna().any(), "quartets: NaN in y!"
    return df, y


datasets = [
    Dataset(
        "asap-dataset",
        asap_label,
        "Composer",
        [".mid", ".xml"],
        legal_filenames=r".+xml_score\.(?:musicxml|mid)",
        friendly_name="asap-scores",
    ),
    Dataset(
        "asap-dataset",
        asap_label,
        "Composer",
        [".mid"],
        legal_filenames=r".*/[A-Z]+\w*.mid",
        friendly_name="asap-performance",
    ),
    Dataset("didone", didone_label, "Aria Title", [".mid", ".xml"]),
    Dataset("EWLD", ewld_label, "Genre", [".mid", ".xml"]),
    Dataset(
        "mass-duos-corpus-josquin-larue",
        jlr_label,
        "Composer",
        [".mid", ".xml"],
        legal_filenames=r".+/XML/.*\.(?:xml|mid)",
        friendly_name="JLR",
    ),
    Dataset("quartets", quartets_label, "Composer", [".mid", ".krn"]),
]


@dataclass
class Task:
    """
    A class representing a task to be performed on a dataset.

    Attributes:
    dataset (Dataset): The dataset to perform the task on.
    feature_set (FeatureSet): The feature set to use for the task.
    extension (str): The file extension of the dataset.
    __loaded (bool): A private attribute to keep track of whether the dataset has been
        loaded.

    Attributes (after __post_init__):
    name (str): The name of the task.

    Attributes (after load_csv):
    x (pd.DataFrame): The feature matrix of the dataset.
    y (pd.Series): The label vector of the dataset.
    filenames_ (pd.Series): The filenames of the dataset.

    Methods:
    __post_init__: A method to initialize the object after it has been created.
    load_csv: A method to load the CSV file and clean it.
    intersect: A method to intersect the filenames of the current Task object with the
        filenames of the Task objects in the input list.
    get_csv_path: A method to get the path of the CSV file.
    """

    dataset: Dataset
    feature_set: FeatureSet
    extension: str
    __loaded: bool = False

    def __post_init__(self):
        assert (
            self.extension in self.dataset.extensions
        ), "Extension not supported by this dataset"
        self.name = (
            self.dataset.friendly_name
            + "-"
            + self.feature_set.name
            + "-"
            + self.extension[1:]
        )

    def load_csv(self):
        """
        A method to load the CSV file and clean it.

        Parameters:
        None

        Returns:
        None

        Raises:
        FileNotFoundError: If the task doesn't have a CSV file.
        """
        if not self.__loaded:
            # load csv
            csv_path = self.get_csv_path()
            if not csv_path.exists():
                raise FileNotFoundError(
                    f"Task doesn't have csv file: {self}, {csv_path}"
                )
            try:
                self.x = pd.read_csv(csv_path)
            except UnicodeDecodeError:
                enc = chardet.detect(open(csv_path, "rb").read())["encoding"]
                self.x = pd.read_csv(csv_path, encoding=enc)

            # make label and removes rows that are not for this data (mainly asap and JLR)
            self.x, self.y, self.filenames_ = self.dataset.parse(
                self.x,
                self.feature_set.filename_col,
                self.feature_set.label_col_selector,
            )
            self.x = self.feature_set.parse(self.x)

            # keep only numeric data
            self.x = self.x.select_dtypes([int, float])

            # take only the first 10 Principal Components
            if S.KEEP_FIRST_10_PC:
                index = self.x.index
                N = 10
                scaler = StandardScaler()
                pca = PCA(n_components=N)
                self.x = pd.DataFrame(
                    pca.fit_transform(scaler.fit_transform(self.x)),
                    index=index,
                    columns=[f"PC{i}" for i in range(N)],
                )

            # remove columns that are not features (only musif)
            self.__loaded = True

    def intersect(self, intersect: List["Task"]):
        """
        A method to intersect the filenames of the current Task object with the
        filenames of the Task objects in the input list.

        Parameters:
        intersect (List["Task"]): A list of Task objects to intersect filenames with.

        Returns:
        None

        Raises:
        N/A
        """
        assert self.__loaded, f"Task {self.name} must be loaded before intersecting"
        intersect_rows = []
        for task in intersect:
            assert task.__loaded, f"Task {task.name} must be loaded before intersecting"
            if not hasattr(task, "x"):
                continue
            if (
                task.dataset.friendly_name == self.dataset.friendly_name
                and task.extension == self.extension
            ):
                intersect_rows.append(task.filenames_)
        intersect_rows = set(intersect_rows[0]).intersection(*intersect_rows)
        idx = self.filenames_.isin(intersect_rows)
        self.x = self.x.loc[idx.values]
        self.y = self.y.loc[idx.values]

    def get_csv_path(self):
        csv_name = self.feature_set.csvname + "-" + self.extension[1:] + ".csv"
        return Path(S.OUTPUT) / self.dataset.name / csv_name


class ConcatTask(Task):
    """
    A class to represent a concatenation task.

    Attributes
    ----------
    tasks : List[Task]
        A list of tasks to be concatenated.

    Methods
    -------
    load_csv()
        Load the csv files of the tasks and concatenate them across columns.
    """

    def __init__(self, tasks: List[Task]):
        self.tasks = tasks
        self.__loaded = False

        assert len(self.tasks) >= 2, "ConcatTask must have at least 2 tasks"
        extensions = [task.extension for task in self.tasks]
        assert all(ext == extensions[0] for ext in extensions), "Extensions must match"
        friendly_names = [task.dataset.friendly_name for task in self.tasks]
        assert all(
            name == friendly_names[0] for name in friendly_names
        ), "Datasets must match"
        super().__init__(
            self.tasks[0].dataset, self.tasks[0].feature_set, extensions[0]
        )

        # self.dataset = self.tasks[0].dataset
        # self.extension = extensions[0]
        feature_set_names = [task.feature_set.name for task in self.tasks]
        self.name = (
            friendly_names[0]
            + "-"
            + "-".join(feature_set_names)
            + "-"
            + extensions[0][1:]
        )

    def load_csv(self):
        """
        Load the csv files of the tasks and concatenate them across columns, using
        the columns with names `feature_set.filename_col` as index of the dataframes.
        """
        if not self.__loaded:
            self.tasks[0].load_csv()
            self.filenames_ = self.tasks[0].filenames_.sort_values()
            self.y = self.tasks[0].y[self.filenames_.index]
            self.x = self.tasks[0].x.loc[self.filenames_.index]
            for task in self.tasks[1:]:
                task.load_csv()
                # forcing the order of the files to be the same
                y = task.y[task.filenames_.sort_values().index]
                x = task.x.loc[task.filenames_.sort_values().index]
                assert np.all(y.values == self.y.values), "Labels must match"
                self.x = pd.concat([self.x, x], axis=1, join="inner")
            self.__loaded = True

    def get_csv_path(self):
        raise NotImplementedError("ConcatTask doesn't have a single CSV file")


concat_tasks = [
    ("musif_native", "jSymbolic"),
    ("musif_native", "music21_native"),
    # ("musif_native", "music21"),
    ("music21_native", "jSymbolic"),
    ("musif_native", "music21_native", "jSymbolic"),
]


def load_task_csvs(tasks):
    # 1. load all csv files
    for t in track(tasks, "Loading CSV files"):
        try:
            t.load_csv()
        except FileNotFoundError:
            print(t.name, "not found")
            continue


def load_tasks():
    """
    Loads tasks from datasets and feature sets, and creates an intersection of files.

    Returns:
    --------
    tasks : list
        A list of Task objects.

    Raises:
    -------
    FileNotFoundError:
        If a csv file is not found while loading.

    """
    tasks = [
        Task(d, f, e)
        for d in datasets
        for e in d.extensions
        for f in feature_sets
        if f.accepts(e)
    ]

    # 1. load all csv files
    load_task_csvs(tasks)

    # 2. use the other csv files to create the intersection
    for t in tasks:
        t.intersect(tasks)

    # 3. adding concat tasks
    concat_tasks = []
    for d in datasets:
        for ext in d.extensions:
            for c in concat_tasks:
                to_concat = []
                for t in tasks:
                    if (
                        t.feature_set.name in c
                        and t.extension == ext
                        and t.dataset.friendly_name == d.friendly_name
                        and type(t) == Task
                    ):
                        to_concat.append(t)
                if len(to_concat) > 1:
                    concat_tasks.append(ConcatTask(to_concat))

    # 4. load concat tasks
    load_task_csvs(concat_tasks)
    tasks += concat_tasks

    logger.info(f"{len(tasks)} tasks loaded")
    return tasks
