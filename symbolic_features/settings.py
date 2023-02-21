import os

# DATASETS = ["datasets/asap-dataset/Bach/Italian_concerto/"]
DATASETS = [f for f in os.scandir('datasets/') if f.is_dir()]
OUTPUT = "features/"

# path to the jSymbolic 2.2 jar file
JSYMBOLIC_EXE = "./tools/jSymbolic_2_2_user/jSymbolic2.jar"
# path to musescore executable (could be /usr/bin/mscore, but version 3.6.2 is recommended)
MUSESCORE = "/home/federico/bin/MuseScore-3.6.2.548021370-x86_64.AppImage"
