import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .utils import AbstractMain, logger, telegram_notify


@dataclass
class Main(AbstractMain):
    datasets: dict = None
    conversion_timeout: float = 120
    mscore_exe: str = None
    hum2mid: str = Path("humdrum-tools") / "humextra" / "bin" / "hum2mid"

    @logger.catch
    def fix_invalid_filenames(self):
        """
        Fix invalid names containing , ; and space. Invalid names are renamed, so they
        will no longer exist.
        """
        for dataset in self.datasets.values():
            dataset = Path(dataset)
            for ext in ["xml", "musicxml", "mxl", "mid", "krn"]:
                for file in dataset.glob(f"**/*.{ext}"):
                    if any(char in file.name for char in [",", ";"]):
                        new_name = str(file).replace(",", "_")
                        new_name = new_name.replace(";", "_")
                        new_name = new_name.replace(" ", "_")
                        logger.info(f"Renaming {file} -> {new_name}")
                        Path(new_name).parent.mkdir(parents=True, exist_ok=True)
                        file.rename(new_name)

    @logger.catch
    def convert2midi(self):
        """
        Add a midi file for each musicxml or kern file
        """
        for dataset in self.datasets.values():
            if "didone" in str(dataset):
                to_remove = Path(dataset) / "midi"
                if to_remove.exists():
                    shutil.rmtree(to_remove)

            for ext in ["xml", "musicxml", "mxl", "krn"]:
                for file in Path(dataset).glob(f"**/*.{ext}"):
                    if file.with_suffix(".mid").exists():
                        logger.info(f"{file} already exists as MIDI, skipping it!")
                        continue

                    if ext == "krn":
                        cmd = [
                            self.hum2mid,
                            file,
                            "-CIPT",
                            "-o",
                            file.with_suffix(".mid"),
                        ]
                    else:
                        cmd = [self.mscore_exe, "-fo", file.with_suffix(".mid"), file]

                    logger.info(f"Converting {file} to MIDI")
                    try:
                        subprocess.run(
                            cmd,
                            stderr=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL,
                            timeout=self.conversion_timeout,
                        )
                    except subprocess.TimeoutExpired:
                        logger.warning(
                            f"Continuing because time expired for file {file}! Try running:\n"
                            + "".join(cmd)
                        )

    # @logger.catch
    # def musicxml2mxl(self):
    #     """
    #     add an mxl file for each *.xml and *.musicxml file
    #     """
    #     for dataset in self.datasets:
    #         dataset = Path(dataset)
    #         for ext in ["xml", "musicxml"]:
    #             for file in dataset.glob(f"**/*.{ext}"):
    #                 mxl_path = file.with_suffix(".mxl")
    #                 logger.info(f"Compressing {file} to {mxl_path}")
    #                 # create a new zipfile object for the output MXL file
    #                 with zipfile.ZipFile(
    #                     mxl_path, "w", zipfile.ZIP_DEFLATED
    #                 ) as mxl_zip:
    #                     # add the MusicXML file to the zipfile object
    #                     mxl_zip.write(file, file.name)


if __name__ == "__main__":
    from fire import Fire

    Fire(Main)
    telegram_notify("Ended!")
