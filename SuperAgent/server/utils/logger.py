"""
Structured logger for the SuperAgent server.

Provides consistent log formatting with session tracking.
"""

import logging
import os
import sys
from contextvars import ContextVar

session_id_var: ContextVar[str] = ContextVar("session_id", default="no-session")


class _SessionFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.session_id = session_id_var.get()  # type: ignore[attr-defined]
        return super().format(record)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
    logger.setLevel(level)
    logger.propagate = False

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        _SessionFormatter(
            "[%(asctime)s] %(levelname)s [%(name)s] [session:%(session_id)s] %(message)s"
        )
    )
    logger.addHandler(handler)
    return logger
