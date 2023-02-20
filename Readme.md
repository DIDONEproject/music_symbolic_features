# Benchamrking symbolic music features

### Dependencies

* Python 3.9 (e.g. via conda or pyenv)
* `pdm`, you barely have three options:
  - `pipx install pdm` (unix-only and user-wide)
  - `pip install pdm` (everywhere, but environment specific)
  - see https://pdm.fming.dev/latest/ for user-wide installation
* `pdm sync`
* MuseScore (4.0.1 has a [bug](https://github.com/musescore/MuseScore/issues/16444), use [3.6.2](https://github.com/musescore/MuseScore/releases/tag/v3.6.2), instead)

### Datasets

Download the following datasets and set the paths to the root of each one in `symbolic_features/settings.py`

1. [Josquin - La Rue]()
2. [ASAP]()
3. [Didone]()
4. [MMD]()
5. [EWLD]()

### Preprocessing

1. **Convert MusicXML to MIDI**: `pdm musicxml2midi`
