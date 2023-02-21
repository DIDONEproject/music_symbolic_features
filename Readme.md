# Benchamrking symbolic music features

### Dependencies

* Python 3.9 (e.g. via conda or pyenv)
* `pdm`, you barely have three options:
  - `pipx install pdm` (unix-only and user-wide)
  - `pip install pdm` (everywhere, but environment specific)
  - see https://pdm.fming.dev/latest/ for user-wide installation
* `pdm sync`
* MuseScore (4.0.1 has a [bug](https://github.com/musescore/MuseScore/issues/16444), use [3.6.2](https://github.com/musescore/MuseScore/releases/tag/v3.6.2), instead)
* jSymbolic 2.2

In `symbolic_features/settings.py` set the paths to MuseScore and jSymbolic executables.

### Datasets

Download the following datasets and set the paths to the root of each one in `symbolic_features/settings.py`

1. [Josquin - La Rue]()
2. [ASAP]()
3. [Didone]()
4. [MMD]()
5. [EWLD]()

### Preprocessing

**Convert MusicXML to MIDI**: `pdm musicxml2midi`. You will need to run `Xvfb :99 & export DISPLAY=:99` if you are running without display (e.g. in a remote ssh session)

### Feature extraction

1. `jSymbolic`: `pdm extract --jsymbolic`. You can check the number of extracted files with:
  * `grep "Successfully extracted" jsymbolic_output.txt | wc -l`
  * `grep "Extracting features" jsymbolic_output.txt | wc -l`
  * The difference between the returned numbers are errored files


### Results

* jSymbolic errored on 3 files from the Didone dataset (MIDI converted from MuseScore)
