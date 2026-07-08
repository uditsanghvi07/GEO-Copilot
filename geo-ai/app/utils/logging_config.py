"""Centralized loguru configuration.

Every module should log via `from loguru import logger` and, ideally,
`logger.bind(module=__name__)` for per-module context. This module wires up
the sinks (console + rotating file) exactly once, at app startup.
"""

import sys

from loguru import logger

from app.config import settings


def configure_logging() -> None:
    """Configure loguru sinks.

    Inputs: none (reads Settings.LOG_LEVEL).
    Outputs: none (side effect: (re)configures the global loguru logger).
    """
    logger.remove()

    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
    )

    logger.add(
        "logs/app.log",
        level=settings.LOG_LEVEL,
        rotation="10 MB",
        retention="7 days",
        enqueue=True,
        backtrace=True,
        diagnose=False,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    logger.info(f"Logging configured (level={settings.LOG_LEVEL}, env={settings.ENVIRONMENT})")
