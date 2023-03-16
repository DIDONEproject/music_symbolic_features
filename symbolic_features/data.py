import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Union

import numpy as np
import pandas as pd
import chardet

from . import settings as S


@dataclass
class FeatureSet:
    name: str
    label_col_selector: Union[List[str], str]
    illegal_cols: List[str]

    def parse(self, df: pd.DataFrame):
        """Remove the illegal columns"""
        if len(self.illegal_cols) > 0:
            df = df.drop(columns=self.illegal_cols)
        return df


feature_sets = [
    FeatureSet("musif", "FileName", ["Id", "WindowId"]),
    FeatureSet("music21", "FileName_0", []),
    # FeatureSet("jsymbolic", "Unnamed: 0", []),
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

    def parse(self, df: pd.DataFrame, label_col_selector: str, remove_col_label=True):
        """Parse a dataframe: remove unwanted rows, create label, and removes label col.
        If nsplits is not None (default) only classes with cardinality > 2*nsplits are
        retained.
        Returns X an y"""

        df, y = self.make_label(df, label_col_selector)

        # removing invalid rows
        idx = df[label_col_selector].str.fullmatch(self.legal_filenames).to_numpy()
        if remove_col_label is not None:
            df = df.drop(columns=label_col_selector)
        df = df.loc[idx]
        y = y.loc[idx]

        # removing classes with little cardinality
        if self.nsplits is not None:
            y_vals, y_freq = np.unique(y, return_counts=True)
            y_vals = y_vals[y_freq > self.nsplits]
            idx = y.isin(y_vals).to_numpy()
            y = y.loc[idx]
            df = df.loc[idx]
        return df, y


def asap_label(df: pd.DataFrame, label_col_selector: str):
    y = df[label_col_selector].str.extract(r".*asap-dataset/(\w+)/.*", expand=False)
    assert not y.isna().any(), "asap: NaN in y!"
    return df, y


def didone_label(df: pd.DataFrame, label_col_selector: str):
    y = df[label_col_selector].str.extract(r".*/xml/(\w+)-.*", expand=False)
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
        """Load the CSV file and clean it"""
        # load csv
        csv_path = self.get_csv_path()
        if not csv_path.exists():
            raise FileNotFoundError(f"Task doesn't have csv file: {self}, {csv_path}")
        try:
            self.x = pd.read_csv(csv_path)
        except UnicodeDecodeError:
            enc = chardet.detect(open(csv_path, "rb").read())["encoding"]
            self.x = pd.read_csv(csv_path, encoding=enc)

        # make label and removes rows that are not for this data (mainly asap and JLR)
        self.x, self.y = self.dataset.parse(self.x, self.feature_set.label_col_selector)

        # remove columns that are not features (only musif)
        self.x = self.feature_set.parse(self.x)

        # keep only numeric data
        self.x = self.x.select_dtypes([int, float])

    def get_csv_path(self):
        csv_name = self.feature_set.name + "-" + self.extension[1:] + ".csv"
        return Path(S.OUTPUT) / self.dataset.name / csv_name


TASKS = [Task(d, f, e) for d in datasets for e in d.extensions for f in feature_sets]
