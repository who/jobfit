"""Tests for PDF resume parsing."""

from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest

from jobfit.errors import EXIT_INPUT
from jobfit.parse_pdf import parse_pdf


@pytest.fixture()
def tmp_dir(tmp_path: Path) -> Path:
    """Return a temporary directory."""
    return tmp_path


def create_pdf(path: Path, pages: list[str]) -> None:
    """Create a PDF file with given text on each page."""
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


class TestParsePdf:
    """PDF parsing extracts text correctly."""

    def test_single_page_pdf(self, tmp_dir: Path) -> None:
        pdf_path = tmp_dir / "resume.pdf"
        create_pdf(pdf_path, ["Hello World, this is a test resume."])
        result = parse_pdf(pdf_path)
        assert "Hello World" in result
        assert "test resume" in result

    def test_multi_page_pdf(self, tmp_dir: Path) -> None:
        pdf_path = tmp_dir / "multi.pdf"
        pages = ["Page one content", "Page two content", "Page three content"]
        create_pdf(pdf_path, pages)
        result = parse_pdf(pdf_path)
        assert "Page one content" in result
        assert "Page two content" in result
        assert "Page three content" in result

    def test_word_count_from_result(self, tmp_dir: Path) -> None:
        pdf_path = tmp_dir / "words.pdf"
        create_pdf(pdf_path, ["one two three four five"])
        result = parse_pdf(pdf_path)
        words = result.split()
        assert len(words) >= 5

    def test_file_not_found(self, tmp_dir: Path) -> None:
        pdf_path = tmp_dir / "nonexistent.pdf"
        with pytest.raises(SystemExit) as exc_info:
            parse_pdf(pdf_path)
        assert exc_info.value.code == EXIT_INPUT

    def test_invalid_file(self, tmp_dir: Path) -> None:
        bad_path = tmp_dir / "notapdf.pdf"
        bad_path.write_text("this is not a pdf")
        with pytest.raises(SystemExit) as exc_info:
            parse_pdf(bad_path)
        assert exc_info.value.code == EXIT_INPUT

    def test_empty_pdf(self, tmp_dir: Path) -> None:
        pdf_path = tmp_dir / "empty.pdf"
        doc = pymupdf.open()
        doc.new_page()  # blank page, no text
        doc.save(str(pdf_path))
        doc.close()
        with pytest.raises(SystemExit) as exc_info:
            parse_pdf(pdf_path)
        assert exc_info.value.code == EXIT_INPUT

    def test_returns_string(self, tmp_dir: Path) -> None:
        pdf_path = tmp_dir / "type.pdf"
        create_pdf(pdf_path, ["Some text here"])
        result = parse_pdf(pdf_path)
        assert isinstance(result, str)
