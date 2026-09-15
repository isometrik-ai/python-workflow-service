"""Application-wide logging configuration."""

import logging
import sys

from app.core.config.app_config import settings

LOGGING_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
# LOGGING_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def _resolve_logging_level(name: str | None) -> int:
    label = (name or "INFO").upper()
    return logging.getLevelNamesMapping().get(label, logging.INFO)


LOGGING_LEVEL = _resolve_logging_level(settings.LOG_LEVEL)

logger = logging.getLogger("app-logger")
logger.setLevel(LOGGING_LEVEL)

if logger.hasHandlers():
    logger.handlers.clear()

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(LOGGING_LEVEL)
console_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))

logger.addHandler(console_handler)
