"""Logging configuration for the DriveNow application.

Sets up the root logger with two handlers on every call to ``setup_logging``:
- A ``StreamHandler`` writing to stdout (consumed by Docker and log aggregators).
- A ``RotatingFileHandler`` writing to ``Settings.LOG_FILE``
  (10 MB per file, 5 rotating backups).

All timestamps are rendered in UTC via a custom ``time.gmtime`` converter,
regardless of the host system timezone.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from app.core.config import get_settings

_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"  # ISO 8601 with timezone


def setup_logging() -> None:
    """Configure the root logger with console and rotating file handlers.

    Clears any existing handlers before attaching new ones, making this
    function safe to call multiple times (idempotent). Also suppresses
    ``uvicorn.access`` and ``sqlalchemy.engine`` to ``WARNING`` so they
    do not pollute application logs at ``INFO`` level.
    """
    settings = get_settings()
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)
    formatter.converter = _gmt_converter  # force UTC in log timestamps

    root = logging.getLogger()
    root.setLevel(level)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    root.addHandler(console)

    log_file = settings.LOG_FILE
    os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def _gmt_converter(*args):
    """Convert a log record timestamp to UTC.

    Assigned to ``logging.Formatter.converter`` so that all ``%(asctime)s``
    fields are rendered in UTC regardless of the host system timezone.

    Args:
        *args: Raw timestamp arguments forwarded from the logging framework.

    Returns:
        A ``time.struct_time`` representing the given time in UTC.
    """
    import time

    return time.gmtime(*args)
