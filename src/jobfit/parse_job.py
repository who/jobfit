"""Job posting parsing routing layer that dispatches to format-specific parsers."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from jobfit.errors import EXIT_INPUT, print_error
from jobfit.parse_pdf import parse_pdf
from jobfit.parse_txt import parse_txt

logger = logging.getLogger("jobfit.parse_job")

# Mapping of supported file extensions to parser functions
SUPPORTED_FORMATS: dict[str, Callable[[Path], str]] = {
    ".pdf": parse_pdf,
    ".txt": parse_txt,
    ".md": parse_txt,
}


def parse_job(path: Path) -> str:
    """Parse a job posting file and return its text content.

    Detects the file format from the extension and dispatches to the
    appropriate parser.

    Args:
        path: Path to the job posting file.

    Returns:
        Extracted text as a string.

    Raises:
        SystemExit: If the format is unsupported or parsing fails.
    """
    suffix = path.suffix.lower()
    logger.debug("Job posting file: path=%s, detected_format=%s", path, suffix)

    if suffix not in SUPPORTED_FORMATS:
        print_error(
            f"unsupported job posting format: {suffix}",
            hint="Supported formats: .pdf, .txt, .md",
            exit_code=EXIT_INPUT,
        )

    parser = SUPPORTED_FORMATS[suffix]
    logger.debug("Dispatching to parser: %s", getattr(parser, "__name__", repr(parser)))
    text = parser(path)
    logger.debug("Parser returned text: length=%d chars", len(text))

    return text
