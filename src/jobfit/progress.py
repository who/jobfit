"""Verbose progress logging to stderr."""

from __future__ import annotations

import sys

# Module-level configuration
_quiet: bool = False


def configure(*, quiet: bool) -> None:
    """Configure progress output settings.

    Args:
        quiet: If True, suppress all progress messages.
    """
    global _quiet  # noqa: PLW0603
    _quiet = quiet


def log_progress(message: str) -> None:
    """Write a progress message to stderr.

    Messages are suppressed when quiet mode is enabled via configure().

    Args:
        message: The progress message to display.
    """
    if _quiet:
        return
    print(message, file=sys.stderr)
