import itertools
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from music21.features.base import allFeaturesAsList, extractorsById
from tqdm import tqdm


def extract(file):
    features = allFeaturesAsList(file)
    features.append([file])
    columns = [x.id for x in extractorsById("all")]
    columns.append("FileName")
    return {
        columns[outer] + f"_{i}": f
        for outer in range(len(columns))
        for i, f in enumerate(features[outer])
    }


def main(dir: str, ext: str, output: str, njobs: int = -1):
    """
    Args:
        dir : directory of the dataset
        ext : extension including '.', e.g. .mid, .krn, .xml; if one of
            [.xml, .musicxml, .mxl] is used, all the others are checked as well
        output : output path of the csv file; extension is added if it's not '.csv'
        njobs : number of processes that will be used; -1 means all virtual cores, 1 means
        no parallel processing
    """

    musicxml_exts = [".xml", ".mxl", ".musicxml"]
    if ext in musicxml_exts:
        exts = musicxml_exts
    else:
        exts = [ext]
    features = []
    for ext in exts:
        files = list(Path(dir).glob("**/*" + ext))
        features += Parallel(n_jobs=njobs)(
            delayed(extract)(file) for file in tqdm(files)
        )

    pd.DataFrame(features).to_csv(
        Path(output).with_suffix(".csv"), index=False
    )


if __name__ == "__main__":
    import fire

    fire.Fire(main)
