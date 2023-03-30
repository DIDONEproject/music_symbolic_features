import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Tuple, Union

import chardet
import numpy as np
import pandas as pd
from rich.progress import track

from . import settings as S

__all_exts__ = (".mid", ".xml", ".musicxml", ".mxl", ".krn")


@dataclass
class FeatureSet:
    name: str
    filename_col: str  # the column used for the filename
    label_col_selector: Union[List[str], str]  # the column used for extracting labels
    illegal_cols: List[str]
    accepted_exts: Tuple[str]

    def parse(self, df: pd.DataFrame):
        """Remove the illegal columns"""
        if len(self.illegal_cols) > 0:
            df = df.drop(columns=self.illegal_cols)
        return df

    def accepts(self, ext: str):
        return ext in self.accepted_exts


feature_sets = [
    FeatureSet("musif", "FileName", "FileName", ["Id", "WindowId"], __all_exts__),
    FeatureSet("music21", "FileName_0", "FileName_0", [], __all_exts__),
    FeatureSet("jsymbolic", "Unnamed: 0", "Unnamed: 0", [], [".mid"]),
]


@dataclass
class Dataset:
    name: str
    make_label: Callable[pd.DataFrame, pd.Series]
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
        remove_col_label=True,
    ):
        """Parse a dataframe: remove unwanted rows, create label, and removes label col.
        If nsplits is not None (default) only classes with cardinality > 2*nsplits are
        retained.
        Returns X an y"""

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
        legal_filenames=r".+xml_score\.(?:xml|mid)",
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
    dataset: Dataset
    feature_set: FeatureSet
    extension: str
    __loaded = False

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
        """Load the CSV file and clean it."""
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

            # remove columns that are not features (only musif)
            self.__loaded = True

    def intersect(self, intersect: List["Task"]):
        intersect_rows = []
        for task in intersect:
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
        csv_name = self.feature_set.name + "-" + self.extension[1:] + ".csv"
        return Path(S.OUTPUT) / self.dataset.name / csv_name


def load_tasks():
    tasks = [
        Task(d, f, e)
        for d in datasets
        for e in d.extensions
        for f in feature_sets
        if f.accepts(e)
    ]
    # forcing the intersection of files:
    # 1. load all csv files
    for t in track(tasks, description="Loading CSV files..."):
        try:
            t.load_csv()
        except FileNotFoundError:
            continue
    # 2. use the other csv files to create the intersection
    for t in tasks:
        t.intersect(tasks)

    return tasks
