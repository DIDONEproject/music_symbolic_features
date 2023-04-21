0. Create zip:
    `sh cluster.sh`
1. Install Python >= 3.10 (es. using pyenv):
    * Install pyenv: `curl https://pyenv.run | bash`
    * Install Python build dependencies `https://github.com/pyenv/pyenv/wiki#suggested-build-environment`
    * Install Python 3.10: `pyenv install 3.10.8`
    * Set-up shell environment: https://github.com/pyenv/pyenv#set-up-your-shell-environment-for-pyenv
    * `pyenv shell 3.10.8`
    * other standard ways for installing python are good as well (e.g. OS package manager)
2. Create a Python environment
    * `python3 -m venv venv`
3. Install dependencies in the environment:
    * Activate it: `source venv/bin/activate`
    * Install pip: `./venv/bin/python -m ensurepip`
    * Install dependencies from `requirements.txt`: `./venv/bin/python -m pip install requirements.txt`
4. Run experiments:
    * test: `sh effectiveness.sh musif didone mid True output.log`
    * uncomment the for loop and run: `sh experiments.sh output.log`
