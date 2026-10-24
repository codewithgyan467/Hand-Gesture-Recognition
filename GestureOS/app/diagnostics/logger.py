"""Structured logging configuration for GestureOS."""

from __future__ import annotations
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional

_LOGGER_INITIALIZED = False


def setup_logger(
    name: str = "GestureOS",
    log_level: int = logging.INFO,
    log_dir: str = "logs",
    log_filename: str = "gestureos.log",
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 3,
) -> logging.Logger:
    """Sets up and configures the central GestureOS logger."""
    global _LOGGER_INITIALIZED
    logger = logging.getLogger(name)

    if _LOGGER_INITIALIZED:
        return logger

    logger.setLevel(log_level)
    logger.propagate = False

    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_filename)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s.%(module)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Rotating File Handler
    try:
        file_handler = RotatingFileHandler(
            log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        sys.stderr.write(f"Warning: Could not initialize log file: {e}\n")

    _LOGGER_INITIALIZED = True
    return logger


def get_logger(module_name: Optional[str] = None) -> logging.Logger:
    base = logging.getLogger("GestureOS")
    if not _LOGGER_INITIALIZED:
        setup_logger()
    if module_name:
        return base.getChild(module_name)
    return base
