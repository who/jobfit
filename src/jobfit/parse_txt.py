"""Plain text resume parsing."""

from __future__ import annotations

from pathlib import Path

from jobfit.errors import EXIT_INPUT, print_error


def parse_txt(path: Path) -> str:
    """Extract text content from a plain text file.

    Args:
        path: Path to the text file.

    Returns:
        File content as a string.

    Raises:
        SystemExit: If the file cannot be read or contains no text.
    """
    if not path.is_file():
        print_error(
            f"Resume file not found: {path}",
            hint="Check the file path and try again.",
            exit_code=EXIT_INPUT,
        )

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except PermissionError:
        print_error(
            f"Permission denied reading file: {path}",
            detail="The file cannot be read due to insufficient permissions.",
            hint="Check file permissions and try again.",
            exit_code=EXIT_INPUT,
        )
    except Exception as e:
        print_error(
            f"Failed to read text file: {path}",
            detail=str(e),
            exit_code=EXIT_INPUT,
        )

    text = text.strip()
    if not text:
        print_error(
            f"No text content found in file: {path}",
            detail="The file appears to be empty or contains only whitespace.",
            hint="Ensure the file contains text content.",
            exit_code=EXIT_INPUT,
        )

    return text
