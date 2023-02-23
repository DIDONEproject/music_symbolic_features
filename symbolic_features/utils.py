import json
import sys
from pathlib import Path
from dataclasses import dataclass, asdict

import notifiers
from loguru import logger
from notifiers.logging import NotificationHandler

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
class AbstractMain():

    def __post_init__(self):
        for name, value in asdict(self).items():
            if value is not None:
                setattr(S, name.upper(), value)
            else:
                setattr(self, name, getattr(S, name.upper(), None))
