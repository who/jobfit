"""Tests for CLI argument parsing and output writing."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from jobfit.errors import EXIT_API, EXIT_GENERAL, EXIT_USAGE
from jobfit.main import main, write_output


@pytest.fixture(autouse=True)
def _set_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set a dummy API key so arg-parsing tests don't fail on key validation."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-dummy")


@pytest.fixture()
def resume_file(tmp_path: Path) -> Path:
    """Create a temporary resume file for CLI tests."""
    f = tmp_path / "resume.txt"
    f.write_text("Test resume content", encoding="utf-8")
    return f


@pytest.fixture(autouse=True)
def _mock_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock the async pipeline so CLI tests don't run the full pipeline."""
    mock_report = "# JobFit Analysis Report\n\n## Overall Match Score: 7/10\n"
    mock_coro = AsyncMock(return_value=mock_report)
    monkeypatch.setattr("jobfit.main._async_pipeline", mock_coro)


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

    def test_valid_required_args_accepted(self, resume_file: Path) -> None:
        # Should not raise
        main(["--url", "https://example.com/job", "--resume", str(resume_file)])


class TestShortFlags:
    """Short flag forms work correctly."""

    def test_short_url_and_resume(self, resume_file: Path) -> None:
        main(["-u", "https://example.com/job", "-r", str(resume_file)])

    def test_short_output(self, resume_file: Path) -> None:
        main(["-u", "https://example.com/job", "-r", str(resume_file), "-o", "out.md"])

    def test_short_quiet(self, resume_file: Path) -> None:
        main(["-u", "https://example.com/job", "-r", str(resume_file), "-q"])

    def test_short_verbose(self, resume_file: Path) -> None:
        main(["-u", "https://example.com/job", "-r", str(resume_file), "-v"])


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

    @staticmethod
    def _valid_args(resume_file: Path) -> list[str]:
        return ["--url", "https://example.com/job", "--resume", str(resume_file)]

    def test_missing_key_exits_5(
        self, monkeypatch: pytest.MonkeyPatch, resume_file: Path
    ) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setattr("jobfit.main.load_dotenv", lambda: None)
        with pytest.raises(SystemExit) as exc_info:
            main(self._valid_args(resume_file))
        assert exc_info.value.code == EXIT_API

    def test_empty_key_exits_5(
        self, monkeypatch: pytest.MonkeyPatch, resume_file: Path
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        with pytest.raises(SystemExit) as exc_info:
            main(self._valid_args(resume_file))
        assert exc_info.value.code == EXIT_API

    def test_whitespace_key_exits_5(
        self, monkeypatch: pytest.MonkeyPatch, resume_file: Path
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "   ")
        with pytest.raises(SystemExit) as exc_info:
            main(self._valid_args(resume_file))
        assert exc_info.value.code == EXIT_API

    def test_error_message_on_stderr(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        resume_file: Path,
    ) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setattr("jobfit.main.load_dotenv", lambda: None)
        with pytest.raises(SystemExit):
            main(self._valid_args(resume_file))
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "ANTHROPIC_API_KEY" in captured.err
        assert "error:" in captured.err

    def test_valid_key_no_error(
        self, monkeypatch: pytest.MonkeyPatch, resume_file: Path
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        # Should not raise on API key validation
        main(self._valid_args(resume_file))


class TestWriteOutput:
    """Tests for the write_output function."""

    _sample_report = "# JobFit Analysis Report\n\n## Overall Match Score: 7/10\n"

    def test_no_output_path_writes_to_stdout(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        write_output(self._sample_report, None)
        captured = capsys.readouterr()
        assert captured.out == self._sample_report

    def test_output_path_creates_file(self, tmp_path: Path) -> None:
        output_file = tmp_path / "report.md"
        write_output(self._sample_report, str(output_file))
        assert output_file.exists()
        assert output_file.read_text(encoding="utf-8") == self._sample_report

    def test_output_file_is_utf8(self, tmp_path: Path) -> None:
        report_with_unicode = "# Report\n\n✅ Match\n❌ Miss\n"
        output_file = tmp_path / "report.md"
        write_output(report_with_unicode, str(output_file))
        content = output_file.read_bytes()
        assert content == report_with_unicode.encode("utf-8")

    def test_existing_file_is_overwritten(self, tmp_path: Path) -> None:
        output_file = tmp_path / "report.md"
        output_file.write_text("old content", encoding="utf-8")
        write_output(self._sample_report, str(output_file))
        assert output_file.read_text(encoding="utf-8") == self._sample_report

    def test_permission_denied_exits_1(self, tmp_path: Path) -> None:
        # Create a read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)
        output_file = readonly_dir / "report.md"
        with pytest.raises(SystemExit) as exc_info:
            write_output(self._sample_report, str(output_file))
        assert exc_info.value.code == EXIT_GENERAL
        # Restore permissions for cleanup
        readonly_dir.chmod(0o755)

    def test_nonexistent_parent_dir_exits_1(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            write_output(self._sample_report, "/nonexistent/dir/report.md")
        assert exc_info.value.code == EXIT_GENERAL

    def test_permission_error_message_on_stderr(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        output_file = tmp_path / "nonexistent_dir" / "report.md"
        with pytest.raises(SystemExit):
            write_output(self._sample_report, str(output_file))
        captured = capsys.readouterr()
        assert "error:" in captured.err

    def test_progress_message_on_success(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from jobfit.progress import configure

        configure(quiet=False)
        output_file = tmp_path / "report.md"
        write_output(self._sample_report, str(output_file))
        captured = capsys.readouterr()
        assert str(output_file) in captured.err
