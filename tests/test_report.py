"""Tests for report formatting functionality."""

from __future__ import annotations

from jobfit.analyze import AnalysisResult
from jobfit.report import format_report


def _make_analysis_result(
    score: int = 7, raw_report: str | None = None
) -> AnalysisResult:
    """Create an AnalysisResult with a well-formed raw_report.

    Args:
        score: The match score (0-10).
        raw_report: Custom raw report text. If None, creates a valid default report.

    Returns:
        AnalysisResult instance with valid report data.
    """
    if raw_report is None:
        raw_report = f"""# JobFit Analysis Report

## Overall Match Score: {score}/10

## Skills Matrix
| Skill | Required | You Have | Match |
|-------|----------|----------|-------|
| Python | Yes | Yes | ✅ |
| Kubernetes | Yes | No | ❌ |

## Experience Alignment
- 5 years of Python development experience aligns well with requirements
- Strong background in web development matches role needs

## Keyword Analysis
- Key terms found: Python, Django, REST APIs
- Missing keywords: Kubernetes, Docker

## Culture Fit Notes
- Collaborative work style mentioned in resume
- Remote work experience aligns with company culture

## Suggestions
- Consider gaining Kubernetes certification
- Add more details about team leadership experience
"""

    return AnalysisResult(
        raw_report=raw_report,
        score=score,
        model="claude-sonnet-4-5-20250929",
    )


class TestFormatReport:
    """Tests for format_report function."""

    def test_valid_report_has_correct_title(self) -> None:
        """Report should start with '# JobFit Analysis Report'."""
        analysis = _make_analysis_result(score=7)
        report = format_report(analysis)

        assert report.startswith("# JobFit Analysis Report")
        lines = report.split("\n")
        assert lines[0] == "# JobFit Analysis Report"

    def test_valid_report_has_correct_score_section(self) -> None:
        """Report should have score section using AnalysisResult.score."""
        analysis = _make_analysis_result(score=8)
        report = format_report(analysis)

        assert "## Overall Match Score: 8/10" in report

        # Test with different score
        analysis = _make_analysis_result(score=3)
        report = format_report(analysis)
        assert "## Overall Match Score: 3/10" in report

    def test_skills_matrix_is_proper_markdown_table(self) -> None:
        """Skills matrix should be a properly formatted markdown table."""
        analysis = _make_analysis_result(score=7)
        report = format_report(analysis)

        assert "## Skills Matrix" in report
        assert "| Skill | Required | You Have | Match |" in report
        assert "|-------|----------|----------|-------|" in report

    def test_all_six_sections_present(self) -> None:
        """Report should contain all 6 required sections."""
        analysis = _make_analysis_result(score=7)
        report = format_report(analysis)

        required_sections = [
            "## Overall Match Score:",
            "## Skills Matrix",
            "## Experience Alignment",
            "## Keyword Analysis",
            "## Culture Fit Notes",
            "## Suggestions",
        ]

        for section in required_sections:
            assert section in report, f"Missing section: {section}"

    def test_sections_appear_in_correct_order(self) -> None:
        """Sections should appear in the correct order."""
        analysis = _make_analysis_result(score=7)
        report = format_report(analysis)

        # Find positions of each section
        score_pos = report.find("## Overall Match Score:")
        skills_pos = report.find("## Skills Matrix")
        experience_pos = report.find("## Experience Alignment")
        keyword_pos = report.find("## Keyword Analysis")
        culture_pos = report.find("## Culture Fit Notes")
        suggestions_pos = report.find("## Suggestions")

        # All should be found
        assert all(
            pos != -1
            for pos in [
                score_pos,
                skills_pos,
                experience_pos,
                keyword_pos,
                culture_pos,
                suggestions_pos,
            ]
        )

        # Check ordering
        assert score_pos < skills_pos
        assert skills_pos < experience_pos
        assert experience_pos < keyword_pos
        assert keyword_pos < culture_pos
        assert culture_pos < suggestions_pos

    def test_match_emojis_present_in_skills_matrix(self) -> None:
        """Skills matrix should contain match emojis (✅/❌)."""
        analysis = _make_analysis_result(score=7)
        report = format_report(analysis)

        # Check for checkmark emoji (match)
        assert "✅" in report
        # Check for cross emoji (miss)
        assert "❌" in report

    def test_experience_alignment_has_bullet_points(self) -> None:
        """Experience Alignment section should have bullet points."""
        analysis = _make_analysis_result(score=7)
        report = format_report(analysis)

        # Find the Experience Alignment section
        exp_section_start = report.find("## Experience Alignment")
        exp_section_end = report.find("## Keyword Analysis")
        exp_section = report[exp_section_start:exp_section_end]

        # Should contain bullet points (-)
        assert "- " in exp_section or "* " in exp_section

    def test_keyword_analysis_has_bullet_points(self) -> None:
        """Keyword Analysis section should have bullet points."""
        analysis = _make_analysis_result(score=7)
        report = format_report(analysis)

        # Find the Keyword Analysis section
        keyword_section_start = report.find("## Keyword Analysis")
        keyword_section_end = report.find("## Culture Fit Notes")
        keyword_section = report[keyword_section_start:keyword_section_end]

        # Should contain bullet points
        assert "- " in keyword_section or "* " in keyword_section

    def test_culture_fit_notes_has_bullet_points(self) -> None:
        """Culture Fit Notes section should have bullet points."""
        analysis = _make_analysis_result(score=7)
        report = format_report(analysis)

        # Find the Culture Fit Notes section
        culture_section_start = report.find("## Culture Fit Notes")
        culture_section_end = report.find("## Suggestions")
        culture_section = report[culture_section_start:culture_section_end]

        # Should contain bullet points
        assert "- " in culture_section or "* " in culture_section

    def test_suggestions_section_has_bullet_points(self) -> None:
        """Suggestions section should have actionable bullet points."""
        analysis = _make_analysis_result(score=7)
        report = format_report(analysis)

        # Find the Suggestions section
        suggestions_section_start = report.find("## Suggestions")
        suggestions_section = report[suggestions_section_start:]

        # Should contain bullet points
        assert "- " in suggestions_section or "* " in suggestions_section

    def test_report_starts_with_correct_header(self) -> None:
        """Report should start with '# JobFit Analysis Report'."""
        analysis = _make_analysis_result(score=7)
        report = format_report(analysis)

        lines = report.split("\n")
        assert lines[0] == "# JobFit Analysis Report"

    def test_different_scores_produce_correct_output(self) -> None:
        """Different scores should produce correct score sections."""
        test_scores = [1, 5, 7, 10]

        for score in test_scores:
            analysis = _make_analysis_result(score=score)
            report = format_report(analysis)

            expected_score_line = f"## Overall Match Score: {score}/10"
            assert expected_score_line in report, f"Failed for score {score}"

    def test_report_is_valid_markdown(self) -> None:
        """Report should be valid Markdown that renders correctly."""
        analysis = _make_analysis_result(score=7)
        report = format_report(analysis)

        # Check markdown structure elements
        assert report.startswith("# ")  # H1 header
        assert "## " in report  # H2 headers
        assert "|" in report  # Table pipes
        assert "- " in report or "* " in report  # Bullet points

        # Should end with newline
        assert report.endswith("\n")

    def test_missing_section_gets_placeholder(self) -> None:
        """Missing sections should get placeholder text."""
        # Create a raw report missing the Culture Fit Notes section
        raw_report = """# JobFit Analysis Report

## Overall Match Score: 6/10

## Skills Matrix
| Skill | Required | You Have | Match |
|-------|----------|----------|-------|
| Python | Yes | Yes | ✅ |

## Experience Alignment
- Good experience

## Keyword Analysis
- Keywords found

## Suggestions
- Keep learning
"""
        analysis = _make_analysis_result(score=6, raw_report=raw_report)
        report = format_report(analysis)

        # Should still have the Culture Fit Notes section
        assert "## Culture Fit Notes" in report
        # Should have placeholder
        assert "_No information provided._" in report

    def test_score_overrides_raw_report_score(self) -> None:
        """AnalysisResult.score should override score in raw_report."""
        # Raw report says 3/10, but AnalysisResult says 9
        raw_report = """# JobFit Analysis Report

## Overall Match Score: 3/10

## Skills Matrix
| Skill | Required | You Have | Match |
|-------|----------|----------|-------|
| Python | Yes | Yes | ✅ |

## Experience Alignment
- Good match

## Keyword Analysis
- All keywords present

## Culture Fit Notes
- Strong fit

## Suggestions
- None needed
"""
        analysis = _make_analysis_result(score=9, raw_report=raw_report)
        report = format_report(analysis)

        # Should use the AnalysisResult score (9), not the raw report score (3)
        assert "## Overall Match Score: 9/10" in report
        assert "## Overall Match Score: 3/10" not in report
