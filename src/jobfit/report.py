"""Report formatting for job-resume fit analysis."""

from __future__ import annotations

import logging

from jobfit.analyze import AnalysisResult

logger = logging.getLogger("jobfit.report")


def format_report(analysis: AnalysisResult) -> str:
    """Format the multi-agent analysis report.

    The raw_report from the multi-agent pipeline is already structured
    with per-agent sections and a score summary table. This function
    ensures consistent formatting.

    Args:
        analysis: The AnalysisResult containing raw_report and score.

    Returns:
        Formatted markdown report string.
    """
    report = analysis.raw_report.strip() + "\n"
    logger.debug("Formatted report: length=%d chars", len(report))
    return report
