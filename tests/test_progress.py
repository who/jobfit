"""Tests for progress logging."""

from __future__ import annotations

import pytest

from jobfit.progress import configure, log_progress


class TestLogProgress:
    """log_progress writes to stderr unless quiet."""

    @pytest.fixture(autouse=True)
    def _reset(self) -> None:
        """Reset progress config before each test."""
        configure(quiet=False)

    def test_writes_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        log_progress("Fetching job posting from https://example.com...")
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "Fetching job posting from https://example.com..." in captured.err

    def test_quiet_suppresses_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        configure(quiet=True)
        log_progress("This should not appear")
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_default_is_not_quiet(self, capsys: pytest.CaptureFixture[str]) -> None:
        configure(quiet=False)
        log_progress("Visible message")
        captured = capsys.readouterr()
        assert "Visible message" in captured.err

    def test_multiple_messages(self, capsys: pytest.CaptureFixture[str]) -> None:
        log_progress("Step 1")
        log_progress("Step 2")
        captured = capsys.readouterr()
        assert "Step 1" in captured.err
        assert "Step 2" in captured.err

    def test_quiet_toggle(self, capsys: pytest.CaptureFixture[str]) -> None:
        log_progress("Before quiet")
        configure(quiet=True)
        log_progress("During quiet")
        configure(quiet=False)
        log_progress("After quiet")
        captured = capsys.readouterr()
        assert "Before quiet" in captured.err
        assert "During quiet" not in captured.err
        assert "After quiet" in captured.err

    def test_word_count_in_message(self, capsys: pytest.CaptureFixture[str]) -> None:
        log_progress("Successfully fetched job posting (1500 words)")
        captured = capsys.readouterr()
        assert "1500 words" in captured.err
