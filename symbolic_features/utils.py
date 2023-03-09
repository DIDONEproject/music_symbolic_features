import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import notifiers
from loguru import logger
from notifiers.logging import NotificationHandler
from psutil import NoSuchProcess, Popen

from . import settings as S

logger.remove()
logger.add(
    sys.stdout, format="{time:YYYY-MM-DD HH:mm:ss}: <lvl>{message}</lvl>", level="INFO"
)
logger.add("errors.log", retention=2, backtrace=True, diagnose=True)
logger.add("errors.short.log", retention=2, backtrace=True, diagnose=False)

telegram = notifiers.get_notifier("telegram")
try:
    auth = json.load(open("./telegram.json"))
except FileNotFoundError:
    telegram_ok = False
else:
    telegram_ok = True
    telegram_handler = NotificationHandler("telegram", defaults=auth)
    logger.add(telegram_handler, level="ERROR")


def telegram_notify(message: str):
    message = str(Path(__file__).parent.parent) + ":\n\n" + message
    if telegram_ok:
        telegram.notify(message=message, **auth)


@dataclass
class AbstractMain:
    """
    Abstract class intended for Main classes with python-fire.
    It allows to change `settings` variables via command line
    """
    def __post_init__(self):
        for name, value in asdict(self).items():
            if value is not None:
                setattr(S, name.upper(), value)
            else:
                setattr(self, name, getattr(S, name.upper(), None))


def benchmark_command(*popen_args, hook=None, **popen_kwargs):
    """
    Given the arguments to run a sub-process, this function runs it and benchmarks the
    cpu time (user + system), the total time, and the RAM used by the sub-process and
    all its children (recursively).
    It optionally run a function (e.g. to stop the process in certain conditions).

    Args
    ---

    *popen_args : any argument for `psutil.Popen`
    hook : a Callable, accepting the following arguments:
        popen : the `psutil.Poepn` object
        children : list of `psutil.Process` referred to the children of the sub-process
        ram_sequence : list of RAM used by the sub-process and all its children
        cpu_times : dictionary with the CPU time taken by the sub-process (key: 'main')
            and all its children (key: PID)
        start_time : time in seconds in which the sub-process was started

        Note that it is not guaranteed that `children` and `popen` still exist. You
        should protect everything in a `tray: ... except psutil.NoSuchProcess: ...`
    **popen_kwargs : any argument for `psutil.Popen`

    Example
    ---

    ```
    def myhook(popen, children, ram, *args):
        if ram[-1] > 3000:
            # TODO: kill children

    benchmark_command(['echo', 'ciao'], stdout=open('afile.txt', 'w'), hook=myhoo)
    ```
    """

    ram_sequence = []
    cpu_times = {"main": 0}
    start_time = time.time()
    logger.info("Benchmarching command:")
    logger.info("     " + ' '.join(popen_args[0]))
    popen = Popen(*popen_args, **popen_kwargs)
    while popen.poll() is None:
        try:
            times = popen.cpu_times()
            cpu_times["main"] = times.user + times.system
            ram = popen.memory_info().rss
            children = popen.children(recursive=True)
        except NoSuchProcess:
            continue

        for child in children:
            try:
                child_times = child.cpu_times()
                ram += child.memory_info().rss
            except NoSuchProcess:
                continue
            cpu_times[child.pid] = child_times.user + child_times.system

        if hook is not None:
            hook(popen, children, ram_sequence, cpu_times, start_time)

        ram_sequence.append(ram / (2**20))
        time.sleep(1)

    cpu_time = sum(cpu_times.values())
    start_time = time.time() - start_time
    return ram_sequence, start_time, cpu_time
