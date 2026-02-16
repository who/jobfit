"""Tests for report formatting functionality."""

from __future__ import annotations

from jobfit.analyze import AgentResult, AnalysisResult
from jobfit.report import format_report


def _make_analysis_result(
    score: int = 7,
    agent_results: list[AgentResult] | None = None,
) -> AnalysisResult:
    """Create an AnalysisResult with a multi-agent report.

    Args:
        score: The composite match score (1-10).
        agent_results: Optional list of agent results.

    Returns:
        AnalysisResult instance with valid report data.
    """
    if agent_results is None:
        agent_results = [
            AgentResult(
                agent_name="Diana Chen",
                raw_analysis="Technical analysis with depth.",
                score=4,
            ),
            AgentResult(
                agent_name="Marcus Webb",
                raw_analysis="People and org health analysis.",
                score=3,
            ),
        ]

    # Build the raw report in the same format as _aggregate_report
    lines = [
        "# JobFit Analysis Report",
        "",
        f"## Overall Match Score: {score}/10",
        "",
        "---",
        "",
    ]
    for result in agent_results:
        lines.append(f"## {result.agent_name} — Score: {result.score}/5")
        lines.append("")
        lines.append(result.raw_analysis)
        lines.append("")
        lines.append("---")
        lines.append("")
    lines.append("## Score Summary")
    lines.append("")
    lines.append("| Evaluator | Score |")
    lines.append("|-----------|-------|")
    for result in agent_results:
        lines.append(f"| {result.agent_name} | {result.score}/5 |")
    lines.append(f"| **Composite** | **{score}/10** |")
    lines.append("")

    raw_report = "\n".join(lines)

    return AnalysisResult(
        raw_report=raw_report,
        score=score,
        model="test-model",
        agent_results=agent_results,
    )


class TestFormatReport:
    """Tests for format_report function."""

    def test_report_starts_with_title(self) -> None:
        analysis = _make_analysis_result(score=7)
        report = format_report(analysis)
        assert report.startswith("# JobFit Analysis Report")

    def test_report_has_overall_score(self) -> None:
        analysis = _make_analysis_result(score=8)
        report = format_report(analysis)
        assert "## Overall Match Score: 8/10" in report

    def test_report_contains_agent_sections(self) -> None:
        analysis = _make_analysis_result(score=7)
        report = format_report(analysis)
        assert "Diana Chen" in report
        assert "Marcus Webb" in report

    def test_report_has_score_summary(self) -> None:
        analysis = _make_analysis_result(score=7)
        report = format_report(analysis)
        assert "## Score Summary" in report
        assert "| Evaluator | Score |" in report

    def test_report_ends_with_newline(self) -> None:
        analysis = _make_analysis_result(score=7)
        report = format_report(analysis)
        assert report.endswith("\n")

    def test_different_scores(self) -> None:
        for score in [1, 5, 7, 10]:
            analysis = _make_analysis_result(score=score)
            report = format_report(analysis)
            assert f"## Overall Match Score: {score}/10" in report

    def test_report_is_valid_markdown(self) -> None:
        analysis = _make_analysis_result(score=7)
        report = format_report(analysis)
        assert report.startswith("# ")
        assert "## " in report
        assert "|" in report
