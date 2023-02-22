import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from psutil import Popen

from . import settings as S
from .utils import logger, telegram_notify


@dataclass
class Main:
    """
    Command-line options override the ones in settings.py!
    """

    datasets: list = None
    mscore_exe: str = None
    jsymbolic_exe: str = None
    jsymbolic: bool = False
    musescore_timeout: float = 120
    output: str = "features/"
    n_trials_extraction: int = 3
    filetype: str = 'midi'

    def __post_init__(self):
        for name, value in asdict(self).items():
            if value is not None:
                setattr(S, name.upper(), value)
            else:
                setattr(self, name, getattr(S, name.upper(), None))

    @logger.catch
    def fix_invalid_filenames(self):
        for dataset in self.datasets:
            for ext in ["xml", "musicxml", "mxl"]:
                for file in Path(dataset).glob(f"**/*.{ext}"):
                    if any(char in file.name for char in [",", ";"]):
                        new_name = file.name.replace(",", "_")
                        new_name = new_name.replace(";", "_")
                        file.rename(new_name)

    @logger.catch
    def musicxml2midi(self):
        for dataset in self.datasets:
            for ext in ["xml", "musicxml", "mxl"]:
                for file in Path(dataset).glob(f"**/*.{ext}"):
                    logger.info(f"Converting {file} to MIDI")
                    cmd = [self.mscore_exe, "-fo", file.with_suffix(".mid"), file]

                    try:
                        subprocess.run(
                            cmd,
                            stderr=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL,
                            timeout=self.musescore_timeout,
                        )
                    except subprocess.TimeoutExpired:
                        logger.warning(
                            f"Continuing because time expired for file {file}! Try running:\n"
                            + "".join(cmd)
                        )

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
        for dataset in self.datasets:
            dataset = Path(dataset)
            output = Path(self.output) / dataset.name
            output.mkdir(exist_ok=True)
            logger.info(f"Using jSymbolic on {dataset}")
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

        avg_ram = np.mean(ram_stats)
        avg_time = sum(time_stats) / n_midi_files
        max_ram = max(ram_stats)
        sum_times = sum(time_stats)
        return self._log_info(n_midi_files, max_ram, avg_ram, sum_times, avg_time)

    def _get_cmd(self, feature_set, dataset, output):
        if feature_set == "jsymbolic":
            return [
                "java",
                "-jar",
                self.jsymbolic_exe,
                "-csv",
                dataset.absolute(),
                output / "jsymbolic",
                output / "jsymbolic_def",
            ]
        if feature_set == "musif":
            return [
                "python",
                "-m",
                "symbolic_features.musif",
                f"--filetype {self.filetype}",
                f"--output_path {output / 'musif.csv'}",
                f"--source_dir {dataset}",
            ]

    def _extract_multiple_trials(self, n_files, feature_set):
        stats = []
        for i in range(self.n_trials_extraction):
            logger.info(f"Trial number {i+1}")
            stat = self._extract_trial(n_files, feature_set)
            stats.append(stat)

        logger.info("_____________")
        logger.info(f"Statistics out of {self.n_trials_extraction} trials")
        logger.info("Averages:")
        stats_avg = np.mean(stats, axis=0)
        self._log_info(n_files, *stats_avg)
        logger.info("Std (1 ddof):")
        stats_std = np.std(stats, axis=0, ddof=1)
        self._log_info(n_files, *stats_std)

    @logger.catch
    def extract(self):
        midi_files = []
        xml_files = []
        for p in self.datasets:
            midi_files += list(Path(p).glob("**/*.mid"))
            xml_files += list(Path(p).glob("**/*.xml"))
            xml_files += list(Path(p).glob("**/*.mxl"))
            xml_files += list(Path(p).glob("**/*.musicxml"))

        if self.jsymbolic:
            self._extract_multiple_trials(len(midi_files), "jsymbolic")
        if self.musif:
            if self.filetype == 'midi':
                n_files = len(midi_files)
            else:
                # xml
                n_files = len(xml_files)
            self._extract_multiple_trials(n_files, "musif")


if __name__ == "__main__":
    from fire import Fire

    Fire(Main)
    telegram_notify("Ended!")
