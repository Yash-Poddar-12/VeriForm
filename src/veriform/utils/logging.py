"""
veriform.utils.logging
======================
Shared logging factory for the entire veriform package.

All modules obtain a logger via:

    from veriform.utils.logging import get_logger
    logger = get_logger(__name__)
"""

from __future__ import annotations

import logging
import sys

from veriform.config import settings

_FMT = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
_DATE_FMT = "%Y-%m-%dT%H:%M:%S"

logging.basicConfig(
    level=settings.log_level,
    format=_FMT,
    datefmt=_DATE_FMT,
    stream=sys.stdout,
)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger with the application-wide log level applied."""
    logger = logging.getLogger(name)
    logger.setLevel(settings.log_level)
    return logger
