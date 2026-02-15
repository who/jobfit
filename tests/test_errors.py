"""Tests for the errors module."""

from __future__ import annotations

import subprocess
import sys

import pytest

from jobfit.errors import (
    EXIT_API,
    EXIT_GENERAL,
    EXIT_INPUT,
    EXIT_NETWORK,
    EXIT_PARSE,
    EXIT_SUCCESS,
    EXIT_USAGE,
    format_error,
    print_error,
)


class TestExitCodes:
    """Exit codes match PRD spec."""

    def test_exit_codes_values(self) -> None:
        assert EXIT_SUCCESS == 0
        assert EXIT_GENERAL == 1
        assert EXIT_USAGE == 2
        assert EXIT_INPUT == 3
        assert EXIT_NETWORK == 4
        assert EXIT_API == 5
        assert EXIT_PARSE == 6


class TestFormatError:
    """Error formatting produces the correct output."""

    def test_brief_only(self) -> None:
        result = format_error("something failed")
        assert result == "error: something failed"

    def test_brief_and_detail(self) -> None:
        result = format_error("something failed", detail="it was bad")
        assert result == "error: something failed\n\n  it was bad"

    def test_brief_and_hint(self) -> None:
        result = format_error("something failed", hint="try again")
        assert result == "error: something failed\n\nhint: try again"

    def test_all_fields(self) -> None:
        result = format_error(
            "ANTHROPIC_API_KEY not set",
            detail="The API key is required to call Claude.",
            hint="export ANTHROPIC_API_KEY=sk-ant-...",
        )
        expected = (
            "error: ANTHROPIC_API_KEY not set\n"
            "\n"
            "  The API key is required to call Claude.\n"
            "\n"
            "hint: export ANTHROPIC_API_KEY=sk-ant-..."
        )
        assert result == expected


class TestPrintError:
    """print_error writes to stderr and exits."""

    def test_exits_with_code(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            print_error("fail", exit_code=EXIT_INPUT)
        assert exc_info.value.code == EXIT_INPUT

    def test_default_exit_code(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            print_error("fail")
        assert exc_info.value.code == EXIT_GENERAL

    def test_outputs_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit):
            print_error("oops", hint="fix it")
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "error: oops" in captured.err
        assert "hint: fix it" in captured.err


class TestNoColor:
    """NO_COLOR env var suppresses ANSI codes."""

    def test_no_ansi_with_no_color(self) -> None:
        """Run a subprocess with NO_COLOR=1 and verify no ANSI escapes."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from jobfit.errors import format_error; "
                    "print(format_error('test', detail='detail', hint='hint'))"
                ),
            ],
            capture_output=True,
            text=True,
            env={**dict(__import__("os").environ), "NO_COLOR": "1"},
        )
        assert "\x1b" not in result.stdout
        assert "\x1b" not in result.stderr
