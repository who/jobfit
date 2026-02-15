"""Tests for TXT resume parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from jobfit.errors import EXIT_INPUT
from jobfit.parse_txt import parse_txt


@pytest.fixture()
def tmp_dir(tmp_path: Path) -> Path:
    """Return a temporary directory."""
    return tmp_path


class TestParseTxt:
    """TXT parsing extracts text correctly."""

    def test_reads_basic_text(self, tmp_dir: Path) -> None:
        txt_path = tmp_dir / "resume.txt"
        txt_path.write_text("Hello world", encoding="utf-8")
        result = parse_txt(txt_path)
        assert result == "Hello world"

    def test_reads_multiline_text(self, tmp_dir: Path) -> None:
        txt_path = tmp_dir / "multi.txt"
        content = "First line\nSecond line\nThird line"
        txt_path.write_text(content, encoding="utf-8")
        result = parse_txt(txt_path)
        assert "First line" in result
        assert "Second line" in result
        assert "Third line" in result

    def test_preserves_newlines(self, tmp_dir: Path) -> None:
        txt_path = tmp_dir / "newlines.txt"
        content = "Line one\nLine two\nLine three"
        txt_path.write_text(content, encoding="utf-8")
        result = parse_txt(txt_path)
        assert result == content
        assert result.count("\n") == 2

    def test_unicode_characters(self, tmp_dir: Path) -> None:
        txt_path = tmp_dir / "unicode.txt"
        content = "Résumé with unicode: café, naïve, 日本語"
        txt_path.write_text(content, encoding="utf-8")
        result = parse_txt(txt_path)
        assert result == content
        assert "Résumé" in result
        assert "café" in result
        assert "日本語" in result

    def test_file_not_found(self, tmp_dir: Path) -> None:
        txt_path = tmp_dir / "nonexistent.txt"
        with pytest.raises(SystemExit) as exc_info:
            parse_txt(txt_path)
        assert exc_info.value.code == EXIT_INPUT

    def test_empty_file(self, tmp_dir: Path) -> None:
        txt_path = tmp_dir / "empty.txt"
        txt_path.write_text("", encoding="utf-8")
        with pytest.raises(SystemExit) as exc_info:
            parse_txt(txt_path)
        assert exc_info.value.code == EXIT_INPUT

    def test_return_type(self, tmp_dir: Path) -> None:
        txt_path = tmp_dir / "type.txt"
        txt_path.write_text("Some text here", encoding="utf-8")
        result = parse_txt(txt_path)
        assert isinstance(result, str)

    def test_word_count(self, tmp_dir: Path) -> None:
        txt_path = tmp_dir / "words.txt"
        txt_path.write_text("one two three four five", encoding="utf-8")
        result = parse_txt(txt_path)
        words = result.split()
        assert len(words) >= 5
        assert "one" in words
        assert "five" in words
