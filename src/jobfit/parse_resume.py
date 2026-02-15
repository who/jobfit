"""Resume parsing routing layer that dispatches to format-specific parsers."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from jobfit.errors import EXIT_INPUT, print_error
from jobfit.parse_docx import parse_docx
from jobfit.parse_pdf import parse_pdf
from jobfit.parse_txt import parse_txt


class ResumeContent(BaseModel):
    """Parsed resume content with metadata."""

    text: str
    format: str
    word_count: int


# Mapping of supported file extensions to parser functions
SUPPORTED_FORMATS = {
    ".pdf": parse_pdf,
    ".docx": parse_docx,
    ".txt": parse_txt,
}


def parse_resume(path: Path) -> ResumeContent:
    """Parse a resume file and return its content.

    Detects the file format from the extension and dispatches to the
    appropriate parser.

    Args:
        path: Path to the resume file.

    Returns:
        ResumeContent with parsed text, format, and word count.

    Raises:
        SystemExit: If the format is unsupported or parsing fails.
    """
    # Get file extension (case-insensitive)
    suffix = path.suffix.lower()

    # Check if format is supported
    if suffix not in SUPPORTED_FORMATS:
        print_error(
            f"unsupported resume format: {suffix}",
            hint="Supported formats: .pdf, .docx, .txt",
            exit_code=EXIT_INPUT,
        )

    # Dispatch to the appropriate parser
    parser = SUPPORTED_FORMATS[suffix]
    text = parser(path)

    # Calculate word count
    word_count = len(text.split())

    # Return structured content
    return ResumeContent(
        text=text,
        format=suffix[1:],  # Remove leading dot (e.g., ".pdf" -> "pdf")
        word_count=word_count,
    )
