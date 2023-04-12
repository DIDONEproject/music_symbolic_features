# Benchamrking symbolic music features

### Dependencies

* Python 3.10 (e.g. via conda or pyenv)
* `pdm`, you barely have three options:
  - `pipx install pdm` (need pipx, recommended)
  - `pip install pdm` (environment specific)
  - see https://pdm.fming.dev/latest/ for other alternatives
* `pdm sync` to create the environment and install python packages
* Alternatively to `pdm`, see `cluster.md` for bare venv approach
* MuseScore: download AppImage (4.0.1 has a [bug](https://github.com/musescore/MuseScore/issues/16444), use [3.6.2](https://github.com/musescore/MuseScore/releases/tag/v3.6.2), instead)
* Java: install using you OS package manager and check that the `java` command is
  available in the PATH
* jSymbolic 2.2: [download](https://sourceforge.net/projects/jmir/files/jSymbolic/jSymbolic%202.2/jSymbolic_2_2_user.zip/download) and unzip
* GCC and make: install using your OS package manager
* `humdrum`: 
  1. `git submodule update`
  2. `cd humdrum-tools`
  3. `make update`
  4. `make`

In `symbolic_features/settings.py` set the paths to MuseScore and jSymbolic executables.

### Datasets

Download the following datasets and set the paths to the root of each one in `symbolic_features/settings.py`

1. [Josquin - La Rue](https://zenodo.org/record/2635499)
2. [ASAP](https://github.com/fosfrancesco/asap-dataset)
3. [Didone]()
4. [EWLD](https://zenodo.org/record/1476555)
4. String quartets:
  * [Haydn](http://kern.ccarh.org/cgi-bin/ksbrowse?type=collection&l=/musedata/haydn/quartet)
  * [Mozart](http://kern.ccarh.org/cgi-bin/ksbrowse?type=collection&l=/musedata/mozart/quartet)
  * [Beethoven](http://kern.ccarh.org/cgi-bin/ksbrowse?type=collection&l=/users/craig/classical/beethoven/quartet)
  * unzip the above three zips into one directory, e.g.: `quartets/haydn`,
    `quartets/mozart`, `quartets/beethoven`


### Preprocessing

**Fix invalid file names**: `pdm fix_names`. This will fix names containing `,` and `;`
that cause errors in csv files.

**Convert any file to MIDI**: `pdm convert2midi`. You will need to run `Xvfb :99 &
export DISPLAY=:99` if you are running without display (e.g. in a remote ssh session)

<!-- **Compress all musicxml (.mxl)**: `pdm musicxml2mxl`. Since different datasets use -->
<!-- different extensions for MusicXML files, we convert them to only one extension. Note -->
<!-- that this command will also compress `.xml` files, so if the dataset contains generix -->
<!-- XML files, those will be compressed as well. -->

### Feature extraction

Reproduce experiments: `./extract_all.sh`

Detailed commands:
1. `jSymbolic`: `pdm extract --jsymbolic --extension .mid`
2. `musif`: 
  * `pdm extract --musif --extension .mid`
  * `pdm extract --musif --extension .xml`
  * `pdm extract --musif --extension .krn`
3. `music21`: 
  * `pdm extract --music21 --extension .mid`
  * `pdm extract --music21 --extension .xml`
  * `pdm extract --music21 --extension .krn`

### Classification accuracy

Reproduce experiments: `pdm validation`

Detailed commands
* `pdm classification`: run all experiments with original features
* `pdm classification --use_first_10_pc`: run all experiments with first 10 Principal
  Components from each task (where a task is a combination of dataset, feature set, and
  extension)
* `pdm plot`: plot the AutoML optimization score across time
* `pdm classification --featureset='music21' --dataset='EWLD' --extension='mid'
  --automl_time=60`: run an
  experiment on a single task for 60 seconds
