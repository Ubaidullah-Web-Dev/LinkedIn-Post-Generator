"""
core/logger.py — Structured logging for the LinkedIn Post Automator.
Replaces all print() / custom_print() calls with proper log levels.
"""

import logging
import sys
from pathlib import Path

from core.constants import LOG_PATH


def setup_logging(level: int = logging.INFO, log_file: Path | None = LOG_PATH) -> None:
    """Configure the root logger with console + file handlers."""
    root = logging.getLogger()

    # Avoid adding duplicate handlers on repeated calls
    if root.handlers:
        return

    root.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler — always present
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(fmt)
    root.addHandler(console)

    # File handler — optional
    if log_file:
        try:
            fh = logging.FileHandler(str(log_file), encoding="utf-8")
            fh.setLevel(level)
            fh.setFormatter(fmt)
            root.addHandler(fh)
        except OSError:
            root.warning("Could not open log file: %s", log_file)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger. Usage: `logger = get_logger(__name__)`."""
    return logging.getLogger(name)
