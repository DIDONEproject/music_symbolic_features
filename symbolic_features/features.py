import time
from dataclasses import dataclass
from pathlib import Path

import chardet
import numpy as np
import pandas as pd
from psutil import Popen

from .utils import AbstractMain, logger, telegram_notify


@dataclass
class Main(AbstractMain):
    """
    Command-line options override the ones in settings.py!
    """

    datasets: list = None
    jsymbolic_jar: str = None
    output: str = "features/"
    n_trials_extraction: int = 3
    extension: str = "*.mid"

    def _log_info(self, n_midi_files, max_ram, avg_ram, sum_times, avg_time):
        logger.info(f"Num processed files: {n_midi_files}")
        logger.info(f"Max RAM (MB): {max_ram:.2e}")
        logger.info(f"Avg RAM (MB): {avg_ram:.2e}")
        logger.info(f"Time (sec): {sum_times:.2e}")
        logger.info(f"Avg Time (sec): {avg_time:.2e}")
        logger.info("_____________")
        return max_ram, avg_ram, sum_times, avg_time

    def _extract_trial(self, n_music_scores, feature_set):
        ram_stats = []
        time_stats = []
        errored = {}
        for dataset in self.datasets:
            dataset = Path(dataset)
            output = Path(self.output) / dataset.name
            output.mkdir(parents=True, exist_ok=True)
            logger.info(f"Using {feature_set} on {dataset}")
            process = Popen(
                self._get_cmd(feature_set, dataset, output),
                stdout=open(feature_set + "_output.txt", "wt"),
            )
            while process.poll() is None:
                ram = process.memory_info().rss
                times = process.cpu_times()
                ram_stats.append(ram / (2**20))
                ttt = times.user + times.system
                time.sleep(1)
            time_stats.append(ttt)
            fname = self._get_csv_name(feature_set, output).with_suffix(".csv")
            enc = chardet.detect(open(fname, "rb").read())["encoding"]
            n_converted = pd.read_csv(fname, encoding=enc).shape[0]
            n_errors = n_music_scores - n_converted
            errored[dataset] = n_errors, n_errors / n_music_scores

        avg_ram = np.mean(ram_stats)
        avg_time = sum(time_stats) / n_music_scores
        max_ram = max(ram_stats)
        sum_times = sum(time_stats)
        return (
            self._log_info(n_music_scores, max_ram, avg_ram, sum_times, avg_time),
            errored,
        )

    def _get_csv_name(self, feature_set, output):
        return output / (feature_set + "-" + self.extension.replace(".", ""))

    def _get_cmd(self, feature_set, dataset, output):
        csv_name = self._get_csv_name(feature_set, output)
        if feature_set == "jsymbolic":
            return [
                "java",
                "-Xmx25g",
                "-jar",
                self.jsymbolic_jar,
                "-csv",
                f'"{dataset.absolute()}"',
                csv_name,
                output / "jsymbolic_def",
            ]
        if feature_set == "musif":
            return [
                "python",
                "-m",
                "symbolic_features.musif",
                self.extension,
                f'"{dataset}"',
                csv_name,
            ]

    def _extract_multiple_trials(self, n_files, feature_set):
        stats = []
        for i in range(self.n_trials_extraction):
            logger.info(f"Trial number {i+1}")
            stat, errors = self._extract_trial(n_files, feature_set)
            stats.append(stat)

        logger.info("_____________")
        logger.info("Number of errors per dataset:self.n_trials_extraction:")
        logger.info(errors)
        logger.info(f"Statistics out of {self.n_trials_extraction} trials")
        logger.info("Averages:")
        stats_avg = np.mean(stats, axis=0)
        self._log_info(n_files, *stats_avg)
        logger.info("Std (1 ddof):")
        stats_std = np.std(stats, axis=0, ddof=1)
        self._log_info(n_files, *stats_std)

    # @logger.catch
    def extract(self, jsymbolic=False, musif=False):
        n_files = 0
        for p in self.datasets:
            n_files += len(list(Path(p).glob(f"**/*{self.extension}")))

        if jsymbolic:
            self._extract_multiple_trials(n_files, "jsymbolic")
        if musif:
            self._extract_multiple_trials(n_files, "musif")


if __name__ == "__main__":
    from fire import Fire

    Fire(Main)
    # telegram_notify("Ended!")
