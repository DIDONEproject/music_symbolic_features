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

```
2023-03-01 08:00:59: Number of errors  and time per dataset:
2023-03-01 08:00:59: {'datasets/quartets': (0, 0.0, 103.32), 'datasets/didone': (14, 0.008526187576126675, 9360.95), 'datasets/asap-dataset': (0, 0.0, 4181.9), 'datasets/mass-duos-corpus-josquin-larue': (0, 0.0, 624.9799999999999), 'datasets/EWLD': (0, 0.0, 3991.41)}
2023-03-01 08:00:59: Statistics out of 3 trials
2023-03-01 08:00:59: Averages:
2023-03-01 08:00:59: Num processed files: {'datasets/quartets': 363, 'datasets/didone': 1642, 'datasets/asap-dataset': 1535, 'datasets/mass-duos-corpus-josquin-larue': 338, 'datasets/EWLD': 4489, 'tot': 8367}
2023-03-01 08:00:59: Max RAM (MB): 1.01e+04
2023-03-01 08:00:59: Avg RAM (MB): 6.72e+03
2023-03-01 08:00:59: Time (sec): 1.88e+04
2023-03-01 08:00:59: Avg Time (sec): 2.24e+00
2023-03-01 08:00:59: _____________
2023-03-01 08:00:59: Std (1 ddof):
2023-03-01 08:00:59: Num processed files: {'datasets/quartets': 363, 'datasets/didone': 1642, 'datasets/asap-dataset': 1535, 'datasets/mass-duos-corpus-josquin-larue': 338, 'datasets/EWLD': 4489, 'tot': 8367}
2023-03-01 08:00:59: Max RAM (MB): 1.00e+03
2023-03-01 08:00:59: Avg RAM (MB): 4.13e+02
2023-03-01 08:00:59: Time (sec): 8.36e+02
2023-03-01 08:00:59: Avg Time (sec): 9.99e-02
2023-03-01 08:00:59: _____________
```

#### musif

##### MIDI

```
2023-02-28 20:11:14: Number of errors  and time per dataset:
2023-02-28 20:11:14: {'datasets/quartets': (0, 0.0, 2.21), 'datasets/didone': (0, 0.0, 4.08), 'datasets/asap-dataset': (0, 0.0, 2.42), 'datasets/mass-duos-corpus-josquin-larue': (0, 0.0, 1.92), 'datasets/EWLD': (0, 0.0, 3.3899999999999997)}
2023-02-28 20:11:14: Statistics out of 3 trials
2023-02-28 20:11:14: Averages:
2023-02-28 20:11:14: Num processed files: {'datasets/quartets': 363, 'datasets/didone': 1642, 'datasets/asap-dataset': 1535, 'datasets/mass-duos-corpus-josquin-larue': 338, 'datasets/EWLD': 4489, 'tot': 8367}
2023-02-28 20:11:14: Max RAM (MB): 1.66e+02
2023-02-28 20:11:14: Avg RAM (MB): 1.24e+02
2023-02-28 20:11:14: Time (sec): 1.66e+01
2023-02-28 20:11:14: Avg Time (sec): 1.99e-03
2023-02-28 20:11:14: _____________
2023-02-28 20:11:14: Std (1 ddof):
2023-02-28 20:11:14: Num processed files: {'datasets/quartets': 363, 'datasets/didone': 1642, 'datasets/asap-dataset': 1535, 'datasets/mass-duos-corpus-josquin-larue': 338, 'datasets/EWLD': 4489, 'tot': 8367}
2023-02-28 20:11:14: Max RAM (MB): 1.99e+00
2023-02-28 20:11:14: Avg RAM (MB): 1.78e+00
2023-02-28 20:11:14: Time (sec): 4.77e+00
2023-02-28 20:11:14: Avg Time (sec): 5.70e-04
2023-02-28 20:11:14: _____________
```
