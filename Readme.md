# Benchamrking symbolic music features

### Dependencies

* Python 3.9 (e.g. via conda or pyenv)
* `pdm`, you barely have three options:
  - `pipx install pdm` (need pipx, recommended)
  - `pip install pdm` (environment specific)
  - see https://pdm.fming.dev/latest/ for other alternatives
* `pdm sync` to create the environment and install python packages
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

**Compress all musicxml (.mxl)**: `pdm musicxml2mxl`. Since different datasets use
different extensions for MusicXML files, we convert them to only one extension. Note
that this command will also compress `.xml` files, so if the dataset contains generix
XML files, those will be compressed as well.

### Feature extraction

1. `jSymbolic`: `pdm extract --jsymbolic`
2. `musif`: 
  * `pdm extract --musif --extension .mid`
  * `pdm extract --musif --extension .mxl`
  * `pdm extract --musif --extension .krn`


### Results

#### jSymbolic 2.2

jSymbolic errored on 11 files from the Didone dataset (MIDI converted from MuseScore)

```
2023-02-25 09:52:06: Number of errors per dataset:self.n_trials_extraction:
2023-02-25 09:52:06: {PosixPath('datasets/quartets'): (8004, 0.9566152742918609), PosixPath('datasets/didone'): (6739, 0.8054260786422852), PosixPath('datasets/asap-dataset'): (6832, 0.8165411736584199), PosixPath('datasets/mass-duos-corpus-josquin-larue'): (8029, 0.9596032030596391), PosixPath('datasets/EWLD'): (3878, 0.46348751045775066)}
2023-02-25 09:52:06: Statistics out of 3 trials
2023-02-25 09:52:06: Averages:
2023-02-25 09:52:06: Num processed files: 8367
2023-02-25 09:52:06: Max RAM (MB): 1.03e+04
2023-02-25 09:52:06: Avg RAM (MB): 7.21e+03
2023-02-25 09:52:06: Time (sec): 2.24e+04
2023-02-25 09:52:06: Avg Time (sec): 2.68e+00
2023-02-25 09:52:06: _____________
2023-02-25 09:52:06: Std (1 ddof):
2023-02-25 09:52:06: Num processed files: 8367
2023-02-25 09:52:06: Max RAM (MB): 5.78e+02
2023-02-25 09:52:06: Avg RAM (MB): 4.31e+02
2023-02-25 09:52:06: Time (sec): 4.52e+03
2023-02-25 09:52:06: Avg Time (sec): 5.40e-01
2023-02-25 09:52:06: _____________
```
