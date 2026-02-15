"""Entry point for the jobfit application."""

from __future__ import annotations

import argparse
import os
import sys

from jobfit import __version__
from jobfit.errors import EXIT_API, EXIT_USAGE, format_error, print_error
from jobfit.progress import configure as configure_progress


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="jobfit",
        description="Check how well a resume matches a job posting.",
        add_help=False,
    )
    parser.add_argument(
        "--url",
        "-u",
        required=True,
        help="URL of the job posting to analyze",
    )
    parser.add_argument(
        "--resume",
        "-r",
        required=True,
        help="Path to resume file (PDF, DOCX, or TXT)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Write report to file instead of stdout",
    )
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=True,
        help="Show step-by-step progress on stderr (default)",
    )
    verbosity.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        default=False,
        help="Suppress progress messages",
    )
    parser.add_argument(
        "--help",
        "-h",
        action="help",
        default=argparse.SUPPRESS,
        help="Show this help message and exit",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"jobfit {__version__}",
        help="Show version number and exit",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Run the jobfit application."""
    parser = build_parser()

    # Override argparse's default error handling to use our exit codes
    def error_handler(message: str) -> None:
        msg = format_error(message, hint="Run 'jobfit --help' for usage information.")
        print(msg, file=sys.stderr)
        sys.exit(EXIT_USAGE)

    parser.error = error_handler  # type: ignore[assignment]

    args = parser.parse_args(argv)

    # Configure progress output based on --quiet flag
    configure_progress(quiet=args.quiet)

    # Validate API key before any network calls
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key.strip():
        print_error(
            "ANTHROPIC_API_KEY environment variable not set",
            hint="Set it with: export ANTHROPIC_API_KEY='your-api-key'",
            exit_code=EXIT_API,
        )


if __name__ == "__main__":
    main()
