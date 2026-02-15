"""PDF resume parsing using PyMuPDF."""

from __future__ import annotations

from pathlib import Path

import pymupdf

from jobfit.errors import EXIT_INPUT, print_error


def parse_pdf(path: Path) -> str:
    """Extract text content from a PDF file.

    Args:
        path: Path to the PDF file.

    Returns:
        Extracted text as a string.

    Raises:
        SystemExit: If the file cannot be read or contains no text.
    """
    if not path.exists():
        print_error(
            f"Resume file not found: {path}",
            hint="Check the file path and try again.",
            exit_code=EXIT_INPUT,
        )

    try:
        doc = pymupdf.open(str(path))
    except pymupdf.FileDataError:
        print_error(
            f"Cannot read PDF file: {path}",
            detail="The file is corrupted or not a valid PDF.",
            hint="Ensure the file is a valid, non-corrupted PDF document.",
            exit_code=EXIT_INPUT,
        )
    except Exception as e:
        if "password" in str(e).lower() or "encrypted" in str(e).lower():
            print_error(
                f"PDF is password-protected: {path}",
                hint="Remove the password protection and try again.",
                exit_code=EXIT_INPUT,
            )
        print_error(
            f"Failed to open PDF file: {path}",
            detail=str(e),
            exit_code=EXIT_INPUT,
        )

    pages: list[str] = []
    for page in doc:
        text = page.get_text()
        if text.strip():
            pages.append(text)
    doc.close()

    full_text = "\n".join(pages)

    if not full_text.strip():
        print_error(
            f"No text content found in PDF: {path}",
            detail="The PDF appears to contain no extractable text.",
            hint="This may be a scanned document. Convert it to text first using OCR.",
            exit_code=EXIT_INPUT,
        )

    return full_text
