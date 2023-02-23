from pathlib import Path

import musif.musescore.constants as musescore_c
import musif.musicxml.constants as musicxml_c
import pandas as pd
from musif.config import ExtractConfiguration
from musif.extract.extract import FeaturesExtractor
from musif.process.processor import DataProcessor

from .utils import logger


def main(filetype: str, source_dir: str, output_path: str, njobs=1):
    """
    Options:
        * filetype: 'midi' or 'musicxml'
        * source_dir: relative path to the directory; searched recursively
        * output_path: relative path to the output file; extension is added or changed
        to 'csv'
    """

    config = ExtractConfiguration(
        None,
        xml_dir=source_dir,
        musescore_dir=None,
        cache_dir='musif_cache/',
        basic_modules=["scoring"],
        features=[
            "core",
            "ambitus",
            "melody",
            "tempo",
            "density",
            "texture",
            "lyrics",
            "scale",
            "key",
            "dynamics",
            "rhythm",
        ],
        parallel=njobs
    )
    if filetype == 'musicxml':
        # trying all the musicxml extensions
        raw_dfs = []
        for musicxml_ext in [".xml", ".mxl", ".musicxml"]:
            musicxml_c.MUSICXML_FILE_EXTENSION = musicxml_ext
            raw_df = FeaturesExtractor(config).extract()
            raw_dfs.append(raw_df)
        raw_df = pd.concat(raw_dfs, ignore_index=True)
    else:
        # midi
        musicxml_c.MUSICXML_FILE_EXTENSION = '.mid'
        raw_df = FeaturesExtractor(config).extract()

    processed_df = DataProcessor(raw_df, None).process().data
    output_path = Path(output_path).with_suffix(".csv")
    processed_df.to_csv(output_path)


if __name__ == "__main__":
    import fire

    fire.Fire(main)
