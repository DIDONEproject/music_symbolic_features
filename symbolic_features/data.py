import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List

import pandas as pd

from . import settings as S


@dataclass
class FeatureSet:
    name: str
    filename_col: str
    illegal_cols: List[str]

    def parse(self, df: pd.DataFrame):
        """Remove the illegal columns"""
        if len(self.illegal_cols) > 0:
            df = df.drop(columns=self.illegal_cols)
        return df


feature_sets = [
    FeatureSet("music21", "FileName_0", []),
    FeatureSet("musif", "FileName", ["Id", "WindowId"]),
    FeatureSet("jsymbolic", "Unnamed: 0", []),
]


@dataclass
class Dataset:
    name: str
    make_label: Callable[pd.DataFrame, pd.Series]
    label_content: str
    extensions: List[str]
    remove_col_label: str = None
    legal_filenames: str = r".*"
    friendly_name: str = None

    def __post_init__(self):
        if self.friendly_name is None:
            self.friendly_name = self.name

    def parse(self, df: pd.DataFrame, filename_col: str):
        """Parse a dataframe: remove unwanted rows, create label, and removes label col.
        Returns X an y"""

        df, y = self.make_label(df, filename_col)
        if self.remove_col_label is not None:
            df = df.drop(columns=self.remove_col_label)

        idx = df[filename_col].str.fullmatch(self.legal_filenames)
        df = df.loc[idx]
        y = y.loc[idx]
        return df, y


def asap_label(df: pd.DataFrame, filename_col: str):
    y = df[filename_col].str.extract(r".*asap-dataset/(\w+)/.*", expand=False)
    return df, y


def didone_label(df: pd.DataFrame, filename_col: str):
    y = df[filename_col].str.extract(r".*/xml/(Did\w+)-.*", expand=False)
    return df, y


def ewld_label(df: pd.DataFrame, filename_col: str):
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
    df = pd.read_sql_query(query, conn)

    # select the rows in the DataFrame that match the database rows
    matching_rows = df[df[filename_col].isin(df["path_leadsheet"])]
    return matching_rows, df["genre"]


def jlr_label(df: pd.DataFrame, filename_col: str):
    y = df[filename_col].str.extract(
        r".*mass-duos-corpus-josquin-larue/(\w+)/.*", expand=False
    )
    return df, y


def quartets_label(df: pd.DataFrame, filename_col: str):
    y = df[filename_col].str.extract(r".*quartets/(\w+)/.*", expand=False)
    return df, y


datasets = [
    Dataset(
        "asap-dataset",
        asap_label,
        "Composer",
        [".mid", ".xml"],
        legal_filenames=r".+xml_score\.(?:xml|mid)",
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

    def __post_init__(self):
        assert self.extension in self.dataset.extensions
        self.name = (
            self.dataset.name + "-" + self.feature_set.name + "-" + self.extension[1:]
        )

    def load_csv(self):
        """Load the CSV file and clean it"""
        # load csv
        csv_path = self.get_csv_path()
        self.x = pd.read_csv(csv_path)

        # make label and removes rows that are not for this data (mainly asap and JLR)
        self.x, self.y = self.dataset.parse(self.x, self.feature_set.filename_col)

        # remove columns that are not features (only musif)
        self.x = self.feature_set.parse(self.x)

    def get_csv_path(self):
        csv_name = self.feature_set.name + "-" + self.extension[1:] + ".csv"
        return Path(S.OUTPUT) / self.dataset.name / csv_name


TASKS = [Task(d, f, e) for d in datasets for e in d.extensions for f in feature_sets]
