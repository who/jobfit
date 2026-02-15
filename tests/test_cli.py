"""Tests for CLI argument parsing."""

from __future__ import annotations

import pytest

from jobfit.errors import EXIT_API, EXIT_USAGE
from jobfit.main import main


@pytest.fixture(autouse=True)
def _set_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set a dummy API key so arg-parsing tests don't fail on key validation."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-dummy")


class TestRequiredArgs:
    """Required flags must be provided."""

    def test_no_args_exits_2(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code == EXIT_USAGE

    def test_missing_resume_exits_2(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["--url", "https://example.com/job"])
        assert exc_info.value.code == EXIT_USAGE

    def test_missing_url_exits_2(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["--resume", "resume.pdf"])
        assert exc_info.value.code == EXIT_USAGE

    def test_missing_args_error_on_stderr(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit):
            main([])
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "error:" in captured.err

    def test_valid_required_args_accepted(self) -> None:
        # Should not raise
        main(["--url", "https://example.com/job", "--resume", "resume.pdf"])


class TestShortFlags:
    """Short flag forms work correctly."""

    def test_short_url_and_resume(self) -> None:
        main(["-u", "https://example.com/job", "-r", "resume.pdf"])

    def test_short_output(self) -> None:
        main(["-u", "https://example.com/job", "-r", "resume.pdf", "-o", "out.md"])

    def test_short_quiet(self) -> None:
        main(["-u", "https://example.com/job", "-r", "resume.pdf", "-q"])

    def test_short_verbose(self) -> None:
        main(["-u", "https://example.com/job", "-r", "resume.pdf", "-v"])


class TestHelpAndVersion:
    """--help and --version flags."""

    def test_help_exits_0(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0

    def test_short_help_exits_0(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["-h"])
        assert exc_info.value.code == 0

    def test_help_shows_all_flags(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit):
            main(["--help"])
        captured = capsys.readouterr()
        expected_flags = [
            "--url",
            "--resume",
            "--output",
            "--verbose",
            "--quiet",
            "--help",
            "--version",
        ]
        for flag in expected_flags:
            assert flag in captured.out

    def test_version_exits_0(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0

    def test_version_prints_version(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit):
            main(["--version"])
        captured = capsys.readouterr()
        assert "jobfit 0.1.0" in captured.out


class TestMutualExclusion:
    """--quiet and --verbose are mutually exclusive."""

    def test_quiet_and_verbose_conflict(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(
                [
                    "--url",
                    "https://example.com/job",
                    "--resume",
                    "resume.pdf",
                    "--quiet",
                    "--verbose",
                ]
            )
        assert exc_info.value.code == EXIT_USAGE


class TestInvalidFlags:
    """Invalid flags produce exit code 2."""

    def test_unknown_flag_exits_2(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["--nonexistent"])
        assert exc_info.value.code == EXIT_USAGE


class TestApiKeyValidation:
    """ANTHROPIC_API_KEY validation at startup."""

    _valid_args = ["--url", "https://example.com/job", "--resume", "resume.pdf"]

    def test_missing_key_exits_5(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(SystemExit) as exc_info:
            main(self._valid_args)
        assert exc_info.value.code == EXIT_API

    def test_empty_key_exits_5(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        with pytest.raises(SystemExit) as exc_info:
            main(self._valid_args)
        assert exc_info.value.code == EXIT_API

    def test_whitespace_key_exits_5(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "   ")
        with pytest.raises(SystemExit) as exc_info:
            main(self._valid_args)
        assert exc_info.value.code == EXIT_API

    def test_error_message_on_stderr(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(SystemExit):
            main(self._valid_args)
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "ANTHROPIC_API_KEY" in captured.err
        assert "error:" in captured.err

    def test_valid_key_no_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        # Should not raise on API key validation
        main(self._valid_args)
