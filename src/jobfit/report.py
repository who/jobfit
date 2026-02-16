"""Report formatting for job-resume fit analysis."""

from __future__ import annotations

import logging
import re

from jobfit.analyze import AnalysisResult

logger = logging.getLogger("jobfit.report")


def format_report(analysis: AnalysisResult) -> str:
    """Format the analysis report to ensure it follows the PRD structure.

    Takes the raw_report from Claude and validates/normalizes it to match
    the exact format specified in the PRD. Ensures all 6 required sections
    are present and the score is correctly set.

    Args:
        analysis: The AnalysisResult containing raw_report and score.

    Returns:
        Formatted markdown report string with correct structure.
    """
    raw = analysis.raw_report.strip()
    score = analysis.score

    # Define the required sections in order
    required_sections = [
        "Skills Matrix",
        "Experience Alignment",
        "Keyword Analysis",
        "Culture Fit Notes",
        "Suggestions",
    ]

    # Extract sections from the raw report
    # Pattern matches ## Section Name and captures content until next ## or end
    section_pattern = r"##\s+(.+?)\n((?:(?!##).)*)"
    matches = re.findall(section_pattern, raw, re.DOTALL | re.MULTILINE)

    # Build a dict of sections from the raw report
    sections = {}
    for section_name, content in matches:
        # Normalize section name (strip whitespace, ignore case for matching)
        normalized_name = section_name.strip()
        # Skip the "Overall Match Score" section since we'll rebuild it
        if "match score" in normalized_name.lower():
            continue
        sections[normalized_name] = content.strip()

    logger.debug("Report sections found: %s", list(sections.keys()))

    # Build the formatted report
    lines = [
        "# JobFit Analysis Report",
        "",
        f"## Overall Match Score: {score}/10",
        "",
    ]

    # Add each required section
    for section_name in required_sections:
        # Try to find the section in the parsed sections (case-insensitive match)
        section_content = None
        for key, value in sections.items():
            if key.lower() == section_name.lower():
                section_content = value
                break

        # Add the section header
        lines.append(f"## {section_name}")

        # Add the section content or a placeholder
        if section_content:
            lines.append(section_content)
        else:
            # Section is missing - add a placeholder
            lines.append("_No information provided._")
            logger.debug("Section missing from raw report: %s", section_name)

        lines.append("")

    result = "\n".join(lines).rstrip() + "\n"
    logger.debug("Formatted report: length=%d chars", len(result))
    return result
