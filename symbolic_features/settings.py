from pathlib import Path

DATASETS = {Path(f).name: f for f in Path('datasets/').iterdir() if f.is_dir()}
OUTPUT = "features/"

# path to the jSymbolic 2.2 jar file
JSYMBOLIC_JAR = "./tools/jSymbolic_2_2_user/jSymbolic2.jar"
# path to musescore executable (could be /usr/bin/mscore, but version 3.6.2 is recommended)
MSCORE_EXE = "/home/federico/bin/MuseScore-3.6.2.548021370-x86_64.AppImage"

SPLITS = 10
AUTOML_TIME = 3600
DUMMY_TRIALS = 1000
