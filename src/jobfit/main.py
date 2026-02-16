"""Entry point for the jobfit application."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from jobfit import __version__
from jobfit.analyze import analyze_fit
from jobfit.errors import (
    EXIT_API,
    EXIT_GENERAL,
    EXIT_INPUT,
    EXIT_USAGE,
    format_error,
    print_error,
)
from jobfit.extract_job import extract_job_text
from jobfit.fetch import fetch_page
from jobfit.parse_resume import parse_resume
from jobfit.progress import configure as configure_progress
from jobfit.progress import log_progress
from jobfit.report import format_report

logger = logging.getLogger("jobfit.cli")


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
        default=False,
        help="Enable debug logging with detailed pipeline information",
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
    load_dotenv()

    parser = build_parser()

    # Override argparse's default error handling to use our exit codes
    def error_handler(message: str) -> None:
        msg = format_error(message, hint="Run 'jobfit --help' for usage information.")
        print(msg, file=sys.stderr)
        sys.exit(EXIT_USAGE)

    parser.error = error_handler  # type: ignore[assignment]

    args = parser.parse_args(argv)

    # Configure progress output and debug logging
    configure_progress(quiet=args.quiet, debug=args.verbose)

    logger.debug(
        "Parsed CLI arguments: url=%s, resume=%s, output=%s",
        args.url,
        args.resume,
        args.output,
    )

    # Validate API key before any network calls
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key.strip():
        print_error(
            "ANTHROPIC_API_KEY environment variable not set",
            hint="Set it with: export ANTHROPIC_API_KEY='your-api-key'",
            exit_code=EXIT_API,
        )
    logger.debug("ANTHROPIC_API_KEY loaded (%s...%s)", api_key[:3], api_key[-3:])

    # Validate resume file exists before starting pipeline
    resume_path = Path(args.resume)
    if not resume_path.exists():
        print_error(
            f"resume file not found: {args.resume}",
            hint="Check that the file path is correct.",
            exit_code=EXIT_INPUT,
        )

    # Parse resume (synchronous)
    log_progress(f"Reading resume from {args.resume}...")
    resume = parse_resume(resume_path)
    log_progress(f"Parsed resume ({resume.word_count} words, {resume.format} format)")
    logger.debug(
        "Resume: path=%s, format=%s, text_length=%d, word_count=%d",
        resume_path,
        resume.format,
        len(resume.text),
        resume.word_count,
    )

    # Run async pipeline (fetch, analyze)
    report = asyncio.run(_async_pipeline(args.url, resume.text))

    # Write output
    write_output(report, args.output)


async def _async_pipeline(url: str, resume_text: str) -> str:
    """Run the async portion of the pipeline: fetch, extract, analyze, format.

    Args:
        url: Job posting URL to fetch.
        resume_text: Parsed resume text.

    Returns:
        Formatted markdown report string.
    """
    # Fetch job posting
    log_progress(f"Fetching job posting from {url}...")
    html = await fetch_page(url)
    logger.debug("Fetched HTML: length=%d chars", len(html))

    # Extract job text from HTML
    job_text = extract_job_text(html)
    word_count = len(job_text.split())
    log_progress(f"Extracted job posting ({word_count} words)")
    logger.debug(
        "Extracted job text: length=%d chars, word_count=%d",
        len(job_text),
        word_count,
    )

    # Analyze fit with multi-agent review board
    log_progress("Running multi-agent review board analysis...")
    analysis = await analyze_fit(job_text, resume_text)
    log_progress(
        f"Analysis complete ({len(analysis.agent_results)} agents, "
        f"score: {analysis.score}/10). Generating report..."
    )
    logger.debug(
        "Analysis result: score=%d, model=%s, report_length=%d",
        analysis.score,
        analysis.model,
        len(analysis.raw_report),
    )

    # Format report
    report = format_report(analysis)
    logger.debug("Formatted report: length=%d chars", len(report))
    return report


def write_output(report: str, output_path: str | None) -> None:
    """Write the report to a file or stdout.

    Args:
        report: The formatted Markdown report string.
        output_path: File path to write to, or None for stdout.
    """
    if output_path is None:
        sys.stdout.write(report)
        return

    path = Path(output_path)
    try:
        path.write_text(report, encoding="utf-8")
    except OSError as exc:
        print_error(
            f"Cannot write to '{output_path}'",
            detail=str(exc),
            exit_code=EXIT_GENERAL,
        )
    log_progress(f"Report saved to {output_path}")


if __name__ == "__main__":
    main()
