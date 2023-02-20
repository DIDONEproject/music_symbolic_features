import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import settings as S
from .utils import logger, telegram_notify


@dataclass
class Main:
    jsymbolic: bool = True
    musescore_timeout: float = 120

    @logger.catch
    def musicxml2midi(self):
        for dataset in S.DATASETS:
            for ext in ["xml", "musicxml", "mxl"]:
                for file in Path(dataset).glob(f"**/*.{ext}"):
                    logger.info(f"Converting {file} to MIDI")
                    cmd = [S.MUSESCORE, "-fo", file.with_suffix(".mid"), file]

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


if __name__ == "__main__":
    from fire import Fire

    Fire(Main)
