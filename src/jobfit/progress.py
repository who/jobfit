"""Verbose progress logging to stderr and debug logging via Python logging."""

from __future__ import annotations

import logging
import sys

# Module-level configuration
_quiet: bool = False

# Package-level logger
logger = logging.getLogger("jobfit")


def configure(*, quiet: bool, debug: bool = False) -> None:
    """Configure progress output and debug logging settings.

    Args:
        quiet: If True, suppress all progress messages.
        debug: If True, enable DEBUG-level logging to stderr.
    """
    global _quiet  # noqa: PLW0603
    _quiet = quiet

    # Configure the jobfit logger
    logger.handlers.clear()

    if debug:
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    else:
        logger.setLevel(logging.WARNING)


def log_progress(message: str) -> None:
    """Write a progress message to stderr.

    Messages are suppressed when quiet mode is enabled via configure().

    Args:
        message: The progress message to display.
    """
    if _quiet:
        return
    print(message, file=sys.stderr)
