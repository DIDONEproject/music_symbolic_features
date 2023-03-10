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
        return self


feature_sets = [
    FeatureSet("music21", "FileName_0", []),
    FeatureSet("musif", "FileName", ["Id", "WindowId"]),
    FeatureSet("jsymbolic", "Unnamed: 0", []),
]


@dataclass
class Dataset:
    name: str
    illegal_filename_fullmatch: str
    make_label: Callable[pd.DataFrame, pd.Serie]
    label_content: str
    extensions: List[str]
    remove_col_label: str = None

    def parse(self, df: pd.DataFrame, filename_col: str):
        """Parse a dataframe: remove unwanted rows, create label, and removes label col.
        Returns X an y"""

        y = self.make_label(df)
        if self.remove_col_label is not None:
            df = df.drop(columns=self.remove_col_label)

        idx = df[filename_col].str.fullmatch(self.illegal_filename_fullmatch)
        df = df.drop(index=idx)
        return df, y


datasets = [
    Dataset("asap-dataset", None, None, "Composer", [".mid", ".xml"]),
    Dataset("didone", None, None, "Aria Title", [".mid", ".xml"]),
    Dataset("EWLD", None, None, "Genre", [".mid", ".xml"]),
    Dataset("mass-duos-corpus-josquin-larue", None, None, "Composer", [".mid", ".xml"]),
    Dataset("quartets", None, None, "Composer", [".mid", ".krn"]),
]


@dataclass
class Task:
    dataset: Dataset
    feature_set: FeatureSet
    extension: str

    def __postinit__(self):
        assert self.extension in self.dataset.extensions
        self.name = (
            self.dataset.name + "-" + self.feature_set.name + "-" + self.extension[1:]
        )

    def load_csv(self):
        """Load the CSV file and clean it"""
        # load csv
        csv_path = self.get_csv_path()
        self.x = pd.read_csv(csv_path)

        # make label and removes rows that are not for this data (mainly asap)
        self.x, self.y = self.dataset.parse(self.x, self.feature_set.filename_col)

        # remove columns that are not features (didone only)
        self.x = self.feature_set.parse(self.x)

    def get_csv_path(self):
        csv_name = self.feature_set.name + "-" + self.extension[1:] + ".csv"
        return Path(S.OUTPUT) / self.dataset.name / csv_name


TASKS = [Task(d, f, e) for d in datasets for e in d.extensions for f in feature_sets]
