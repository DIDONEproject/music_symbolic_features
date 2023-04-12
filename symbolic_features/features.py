from dataclasses import dataclass
from pathlib import Path

import chardet
import numpy as np
import pandas as pd

from .utils import AbstractMain, benchmark_command, logger, telegram_notify


@dataclass
class Main(AbstractMain):
    """
    Command-line options override the ones in settings.py!
    """

    datasets: dict = None
    jsymbolic_jar: str = None
    output: str = "features/"
    n_trials_extraction: int = 2
    extension: str = ".mid"

    def _log_info(
        self, n_midi_files, max_ram, avg_ram, sum_times, avg_time, sum_rtimes, avg_rtime
    ):
        logger.info(f"Num processed files: {n_midi_files}")
        logger.info(f"Max RAM (MB): {max_ram:.2e}")
        logger.info(f"Avg RAM (MB): {avg_ram:.2e}")
        logger.info(f"CPU Time (sec): {sum_times:.2e}")
        logger.info(f"CPU Avg Time (sec): {avg_time:.2e}")
        logger.info(f"Real Time (sec): {sum_rtimes:.2e}")
        logger.info(f"Real Avg Time (sec): {avg_rtime:.2e}")
        logger.info("_____________")
        return max_ram, avg_ram, sum_times, avg_time, sum_rtimes, avg_rtime

    def _extract_trial(self, n_music_scores, feature_set):
        ram_stats = []
        cpu_times = []
        real_times = []
        errored = {}
        for dataset in self.datasets.values():
            dataset = Path(dataset)
            output = Path(self.output) / dataset.name
            output.mkdir(parents=True, exist_ok=True)
            if n_music_scores[str(dataset)] == 0:
                # skip datasets that have no files with this extension
                continue
            if '-harm' in feature_set:
                # skip datasets that have no musescore files
                if not (dataset / 'musescore').exists():
                    continue
            logger.info(f"Using {feature_set} on {dataset} extension {self.extension}")
            cmd = self._get_cmd(feature_set, dataset, output)
            ram_sequence, real_time, cpu_time = benchmark_command(
                cmd,
                stdout=open(feature_set + "_output.txt", "wt"),
                stderr=open(feature_set + "_errs.txt", "wt"),
            )
            ram_stats += ram_sequence
            cpu_times.append(cpu_time)
            real_times.append(real_time)

            fname = self._get_csv_name(feature_set, output).with_suffix(".csv")
            enc = chardet.detect(open(fname, "rb").read())["encoding"]
            n_converted = pd.read_csv(fname, encoding=enc).shape[0]
            n_errors = n_music_scores[str(dataset)] - n_converted
            errored[str(dataset)] = {
                "n_errors": n_errors,
                "ratio_errors": n_errors / n_music_scores[str(dataset)],
                "cpu_time": cpu_time,
                "clock_time": real_time,
            }

        avg_ram = np.mean(ram_stats)
        avg_time = sum(cpu_times) / n_music_scores["tot"]
        avg_rtime = sum(real_times) / n_music_scores["tot"]
        max_ram = max(ram_stats)
        sum_times = sum(cpu_times)
        sum_rtimes = sum(real_times)
        return (
            self._log_info(
                n_music_scores,
                max_ram,
                avg_ram,
                sum_times,
                avg_time,
                sum_rtimes,
                avg_rtime,
            ),
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
                str(dataset.absolute()),
                str(csv_name),
                str(output / "jsymbolic_def"),
            ]
        elif feature_set == "musif":
            return [
                "python",
                "-m",
                "musif",
                "-e",
                self.extension,
                "-s",
                str(dataset),
                "-o",
                str(csv_name),
            ]
        elif feature_set == "music21":
            return [
                "python",
                "-m",
                "symbolic_features.music21",
                str(dataset),
                self.extension,
                str(csv_name),
            ]
        elif feature_set == "musif-harm":
            return [
                "python",
                "-m",
                "musif",
                "-e",
                self.extension,
                "-s",
                str(dataset),
                "--harm",
                str(dataset / "musescore"),
                "-o",
                str(csv_name),
            ]

    def _extract_multiple_trials(self, n_files, feature_set):
        stats = []
        for i in range(self.n_trials_extraction):
            logger.info(f"Trial number {i+1}")
            stat, errors = self._extract_trial(n_files, feature_set)
            stats.append(stat)

        logger.info("_____________")
        logger.info("Number of errors  and time per dataset:")
        logger.info(errors)
        logger.info(f"Statistics out of {self.n_trials_extraction} trials")
        logger.info("Averages:")
        stats_avg = np.mean(stats, axis=0)
        self._log_info(n_files, *stats_avg)
        logger.info("Std (1 ddof):")
        stats_std = np.std(stats, axis=0, ddof=1)
        self._log_info(n_files, *stats_std)

    # @logger.catch
    def extract(self, feature_set):
        n_files = {}
        extensions = (
            [".xml", ".musicxml", ".mxl"]
            if self.extension in [".xml", ".musicxml", ".mxl"]
            else [self.extension]
        )
        for p in self.datasets.values():
            p = Path(p)
            n_files[str(p)] = sum(
                1 for ext in extensions for f in p.glob(f"**/*{ext}") if f.is_file()
            )
        n_files["tot"] = sum(n_files.values())
        self._extract_multiple_trials(n_files, feature_set)


if __name__ == "__main__":
    from fire import Fire

    Fire(Main)
    telegram_notify("Ended!")
