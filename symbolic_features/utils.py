import json
import sys

import notifiers
from loguru import logger
from notifiers.logging import NotificationHandler

logger.remove()
logger.add(
    sys.stdout, format="{time:YYYY-MM-DD HH:mm:ss}: <lvl>{message}</lvl>", level="INFO"
)
logger.add("errors.log", retention=0, backtrace=True, diagnose=True)
logger.add("errors.short.log", retention=0, backtrace=True, diagnose=False)

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
    if telegram_ok:
        telegram.notify(message=message, **auth)
