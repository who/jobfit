"""Tests for resume parsing routing layer."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jobfit.errors import EXIT_INPUT
from jobfit.parse_resume import ResumeContent, parse_resume


@pytest.fixture()
def tmp_dir(tmp_path: Path) -> Path:
    """Return a temporary directory."""
    return tmp_path


class TestParseResume:
    """Resume parsing routes to correct parsers and returns structured content."""

    def test_parse_txt_file(self, tmp_dir: Path) -> None:
        """Parse a real TXT file and verify ResumeContent fields."""
        txt_path = tmp_dir / "resume.txt"
        content = "Software Engineer with 5 years of experience in Python development"
        txt_path.write_text(content, encoding="utf-8")

        result = parse_resume(txt_path)

        assert isinstance(result, ResumeContent)
        assert result.text == content
        assert result.format == "txt"
        assert result.word_count == 10

    def test_parse_pdf_dispatches(self, tmp_dir: Path) -> None:
        """Dispatch to parse_pdf and return correctly formatted result."""
        pdf_path = tmp_dir / "resume.pdf"

        # Create a mock parser function
        mock_parser = MagicMock(return_value="mocked pdf text")

        # Patch the SUPPORTED_FORMATS dictionary
        with patch.dict("jobfit.parse_resume.SUPPORTED_FORMATS", {".pdf": mock_parser}):
            result = parse_resume(pdf_path)

            mock_parser.assert_called_once_with(pdf_path)
            assert result.text == "mocked pdf text"
            assert result.format == "pdf"
            assert result.word_count == 3

    def test_parse_docx_dispatches(self, tmp_dir: Path) -> None:
        """Dispatch to parse_docx and return correctly formatted result."""
        docx_path = tmp_dir / "resume.docx"

        # Create a mock parser function
        mock_parser = MagicMock(return_value="mocked docx text content")

        # Patch the SUPPORTED_FORMATS dictionary
        formats_patch = {".docx": mock_parser}
        with patch.dict("jobfit.parse_resume.SUPPORTED_FORMATS", formats_patch):
            result = parse_resume(docx_path)

            mock_parser.assert_called_once_with(docx_path)
            assert result.text == "mocked docx text content"
            assert result.format == "docx"
            assert result.word_count == 4

    def test_case_insensitive_extension(self, tmp_dir: Path) -> None:
        """Handle uppercase extensions and normalize format to lowercase."""
        pdf_path = tmp_dir / "RESUME.PDF"

        # Create a mock parser function
        mock_parser = MagicMock(return_value="uppercase extension test")

        # Patch the SUPPORTED_FORMATS dictionary with lowercase key
        with patch.dict("jobfit.parse_resume.SUPPORTED_FORMATS", {".pdf": mock_parser}):
            result = parse_resume(pdf_path)

            mock_parser.assert_called_once_with(pdf_path)
            assert result.format == "pdf"  # lowercase
            assert result.word_count == 3

    def test_unsupported_format_exits(self, tmp_dir: Path) -> None:
        """Exit with EXIT_INPUT code for unsupported file formats."""
        rtf_path = tmp_dir / "resume.rtf"
        rtf_path.write_text("some content")

        with pytest.raises(SystemExit) as exc_info:
            parse_resume(rtf_path)

        assert exc_info.value.code == EXIT_INPUT

    def test_unsupported_format_error_message(
        self, tmp_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Print helpful error message for unsupported formats."""
        rtf_path = tmp_dir / "resume.rtf"
        rtf_path.write_text("some content")

        with pytest.raises(SystemExit):
            parse_resume(rtf_path)

        captured = capsys.readouterr()
        assert "error: unsupported resume format: .rtf" in captured.err
        assert "hint: Supported formats: .pdf, .docx, .txt" in captured.err

    def test_word_count_calculation(self, tmp_dir: Path) -> None:
        """Calculate word count correctly from parsed text."""
        txt_path = tmp_dir / "words.txt"
        txt_path.write_text("one two three four five", encoding="utf-8")

        result = parse_resume(txt_path)

        assert result.word_count == 5
        assert "one" in result.text
        assert "five" in result.text

    def test_resume_content_model(self) -> None:
        """ResumeContent Pydantic model validates correctly."""
        content = ResumeContent(
            text="Test resume content here",
            format="pdf",
            word_count=4,
        )

        assert content.text == "Test resume content here"
        assert content.format == "pdf"
        assert content.word_count == 4
        assert isinstance(content, ResumeContent)

    def test_word_count_with_multiple_spaces(self, tmp_dir: Path) -> None:
        """Handle multiple spaces between words in word count."""
        txt_path = tmp_dir / "spaces.txt"
        txt_path.write_text("word1  word2   word3", encoding="utf-8")

        result = parse_resume(txt_path)

        # Python's split() handles multiple spaces correctly
        assert result.word_count == 3

    def test_word_count_with_newlines(self, tmp_dir: Path) -> None:
        """Count words correctly across multiple lines."""
        txt_path = tmp_dir / "multiline.txt"
        content = "First line has words\nSecond line too\nThird"
        txt_path.write_text(content, encoding="utf-8")

        result = parse_resume(txt_path)

        assert result.word_count == 8

    def test_returns_resume_content_type(self, tmp_dir: Path) -> None:
        """Return value is always a ResumeContent instance."""
        txt_path = tmp_dir / "resume.txt"

        # Create a mock parser function
        mock_parser = MagicMock(return_value="test content")

        with patch.dict("jobfit.parse_resume.SUPPORTED_FORMATS", {".txt": mock_parser}):
            result = parse_resume(txt_path)

            assert isinstance(result, ResumeContent)
            assert hasattr(result, "text")
            assert hasattr(result, "format")
            assert hasattr(result, "word_count")
