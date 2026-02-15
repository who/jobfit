"""Structured error handling with exit codes and formatted error messages."""

from __future__ import annotations

import os
import sys

# Exit codes per PRD spec
EXIT_SUCCESS = 0
EXIT_GENERAL = 1
EXIT_USAGE = 2
EXIT_INPUT = 3
EXIT_NETWORK = 4
EXIT_API = 5
EXIT_PARSE = 6


def format_error(
    brief: str,
    detail: str | None = None,
    hint: str | None = None,
) -> str:
    """Format an error message in the standard format.

    Format:
        error: [brief]

          [detail]

        hint: [suggestion]
    """
    lines = [f"error: {brief}"]
    if detail:
        lines.append("")
        lines.append(f"  {detail}")
    if hint:
        lines.append("")
        lines.append(f"hint: {hint}")
    return "\n".join(lines)


def print_error(
    brief: str,
    detail: str | None = None,
    hint: str | None = None,
    exit_code: int = EXIT_GENERAL,
) -> None:
    """Print a formatted error to stderr and exit with the given code."""
    msg = format_error(brief, detail, hint)
    print(msg, file=sys.stderr)
    sys.exit(exit_code)


def _supports_color() -> bool:
    """Check if stderr supports ANSI color codes."""
    if os.environ.get("NO_COLOR"):
        return False
    return hasattr(sys.stderr, "isatty") and sys.stderr.isatty()
