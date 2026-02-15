"""Tests for Claude API job-resume fit analysis."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import pytest

from jobfit.analyze import AnalysisResult, analyze_fit
from jobfit.errors import EXIT_API


def _make_response(text: str) -> MagicMock:
    """Create a mock API response with the given text content."""
    content_block = MagicMock()
    content_block.text = text
    response = MagicMock()
    response.content = [content_block]
    return response


def _make_valid_report(score: int = 7) -> str:
    """Create a valid analysis report with all required sections."""
    return f"""# JobFit Analysis Report

## Overall Match Score: {score}/10

## Skills Matrix
| Skill | Required | You Have | Match |
|-------|----------|----------|-------|
| Python | Yes | Yes | ✅ |

## Experience Alignment
- Strong alignment with 5 years experience.

## Keyword Analysis
- Key terms found: Python, Django

## Culture Fit Notes
- Good cultural alignment.

## Suggestions
- Consider adding Kubernetes experience.
"""


class TestAnalysisResult:
    """Tests for AnalysisResult Pydantic model."""

    def test_valid_construction(self) -> None:
        """AnalysisResult should construct with valid fields."""
        result = AnalysisResult(
            raw_report="# Report",
            score=8,
            model="claude-sonnet-4-5-20250929",
        )
        assert result.raw_report == "# Report"
        assert result.score == 8
        assert result.model == "claude-sonnet-4-5-20250929"

    def test_score_is_int(self) -> None:
        """Score field should accept integer values."""
        result = AnalysisResult(
            raw_report="test",
            score=10,
            model="test-model",
        )
        assert isinstance(result.score, int)
        assert result.score == 10


class TestAnalyzeFitSuccess:
    """Tests for successful API calls."""

    async def test_returns_analysis_result(self) -> None:
        """analyze_fit() should return AnalysisResult on success."""
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = _make_response(_make_valid_report(7))

        with patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_client
            result = await analyze_fit(
                job_text="Senior Python Developer needed",
                resume_text="Python developer with 5 years experience",
            )

        assert isinstance(result, AnalysisResult)
        assert result.score == 7
        assert "JobFit Analysis Report" in result.raw_report
        assert result.model == "claude-sonnet-4-5-20250929"

    async def test_default_model(self) -> None:
        """analyze_fit() should use claude-sonnet-4-5-20250929 by default."""
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = _make_response(_make_valid_report(5))

        with patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_client
            result = await analyze_fit(
                job_text="Job posting",
                resume_text="Resume text",
            )

        assert result.model == "claude-sonnet-4-5-20250929"
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4-5-20250929"

    async def test_custom_model(self) -> None:
        """analyze_fit() should accept custom model parameter."""
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = _make_response(_make_valid_report(6))

        with patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_client
            result = await analyze_fit(
                job_text="Job posting",
                resume_text="Resume text",
                model="claude-opus-4-6",
            )

        assert result.model == "claude-opus-4-6"
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-opus-4-6"

    async def test_prompt_contains_job_and_resume_text(self) -> None:
        """Prompt should contain job text and resume text with delimiters."""
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = _make_response(_make_valid_report(8))

        with patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_client
            await analyze_fit(
                job_text="Senior Python Engineer - 5 years exp required",
                resume_text="Python developer with 6 years experience at FAANG",
            )

        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        user_message = call_kwargs["messages"][0]["content"]

        # Check delimiters separate job and resume
        assert "=== JOB POSTING ===" in user_message
        assert "=== RESUME ===" in user_message
        assert "=== END ===" in user_message

        # Check actual content is present
        assert "Senior Python Engineer - 5 years exp required" in user_message
        assert "Python developer with 6 years experience at FAANG" in user_message

    async def test_prompt_requests_all_six_sections(self) -> None:
        """Prompt should request all 6 required sections."""
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = _make_response(_make_valid_report(7))

        with patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_client
            await analyze_fit(
                job_text="Job posting",
                resume_text="Resume text",
            )

        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        system_message = call_kwargs["system"]
        user_message = call_kwargs["messages"][0]["content"]

        # Check system message mentions all sections
        assert "Overall Match Score" in system_message
        assert "Skills Matrix" in system_message
        assert "Experience Alignment" in system_message
        assert "Keyword Analysis" in system_message
        assert "Culture Fit Notes" in system_message
        assert "Suggestions" in system_message

        # Check user message provides format for all sections
        assert "## Overall Match Score:" in user_message
        assert "## Skills Matrix" in user_message
        assert "## Experience Alignment" in user_message
        assert "## Keyword Analysis" in user_message
        assert "## Culture Fit Notes" in user_message
        assert "## Suggestions" in user_message

    async def test_extracts_correct_score(self) -> None:
        """Should correctly extract score from various formats."""
        test_cases = [
            ("## Overall Match Score: 1/10", 1),
            ("## Overall Match Score: 5/10", 5),
            ("## Overall Match Score: 10/10", 10),
            ("##Overall Match Score:9/10", 9),  # No spaces
            ("## overall match score: 7/10", 7),  # Lowercase
        ]

        for report_text, expected_score in test_cases:
            mock_client = AsyncMock()
            full_report = f"# Report\n{report_text}\n## Skills Matrix\ntest"
            mock_client.messages.create.return_value = _make_response(full_report)

            with patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic:
                mock_anthropic.return_value = mock_client
                result = await analyze_fit(
                    job_text="Job",
                    resume_text="Resume",
                )

            assert result.score == expected_score


class TestAnalyzeFitErrors:
    """Tests for API error handling."""

    async def test_authentication_error_exits_5(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """AuthenticationError should exit with code 5 and show auth message."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_client.messages.create.side_effect = anthropic.AuthenticationError(
            "Invalid API key",
            response=mock_response,
            body=None,
        )

        with patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_client
            with pytest.raises(SystemExit) as exc_info:
                await analyze_fit(
                    job_text="Job posting",
                    resume_text="Resume text",
                )

        assert exc_info.value.code == EXIT_API
        assert exc_info.value.code == 5
        captured = capsys.readouterr()
        assert "authentication" in captured.err.lower()

    async def test_rate_limit_error_exits_5(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """RateLimitError should exit with code 5 and show rate limit hint."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_client.messages.create.side_effect = anthropic.RateLimitError(
            "Rate limit exceeded",
            response=mock_response,
            body=None,
        )

        with patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_client
            with pytest.raises(SystemExit) as exc_info:
                await analyze_fit(
                    job_text="Job posting",
                    resume_text="Resume text",
                )

        assert exc_info.value.code == EXIT_API
        assert exc_info.value.code == 5
        captured = capsys.readouterr()
        assert "rate limit" in captured.err.lower()

    async def test_api_status_error_exits_5(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """APIStatusError should exit with code 5 and show server error."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 500

        # Create proper APIStatusError
        error = anthropic.APIStatusError(
            "Internal server error",
            response=mock_response,
            body=None,
        )
        error.status_code = 500
        error.message = "Internal server error"

        mock_client.messages.create.side_effect = error

        with patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_client
            with pytest.raises(SystemExit) as exc_info:
                await analyze_fit(
                    job_text="Job posting",
                    resume_text="Resume text",
                )

        assert exc_info.value.code == EXIT_API
        assert exc_info.value.code == 5
        captured = capsys.readouterr()
        assert "server error" in captured.err.lower()
        assert "500" in captured.err

    async def test_api_connection_error_exits_5(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """APIConnectionError should exit with code 5 and show connection error."""
        mock_client = AsyncMock()
        mock_request = MagicMock()
        mock_client.messages.create.side_effect = anthropic.APIConnectionError(
            message="Connection timeout",
            request=mock_request,
        )

        with patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_client
            with pytest.raises(SystemExit) as exc_info:
                await analyze_fit(
                    job_text="Job posting",
                    resume_text="Resume text",
                )

        assert exc_info.value.code == EXIT_API
        assert exc_info.value.code == 5
        captured = capsys.readouterr()
        assert "connection" in captured.err.lower()

    async def test_generic_exception_exits_5(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Generic Exception should exit with code 5."""
        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = Exception("Unexpected error")

        with patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_client
            with pytest.raises(SystemExit) as exc_info:
                await analyze_fit(
                    job_text="Job posting",
                    resume_text="Resume text",
                )

        assert exc_info.value.code == EXIT_API
        assert exc_info.value.code == 5
        captured = capsys.readouterr()
        assert "error" in captured.err.lower()

    async def test_client_init_error_exits_5(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Client initialization failure should exit with code 5."""
        with patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_anthropic.side_effect = Exception("Missing API key")
            with pytest.raises(SystemExit) as exc_info:
                await analyze_fit(
                    job_text="Job posting",
                    resume_text="Resume text",
                )

        assert exc_info.value.code == EXIT_API
        assert exc_info.value.code == 5
        captured = capsys.readouterr()
        assert "failed to initialize" in captured.err.lower()
        assert "ANTHROPIC_API_KEY" in captured.err


class TestScoreParsing:
    """Tests for score extraction from API response."""

    async def test_valid_score_extracted(self) -> None:
        """Should extract valid score from response."""
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = _make_response(_make_valid_report(7))

        with patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_client
            result = await analyze_fit(
                job_text="Job posting",
                resume_text="Resume text",
            )

        assert result.score == 7

    async def test_missing_score_exits_5(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Missing score in response should exit with code 5."""
        mock_client = AsyncMock()
        # Response without valid score line
        invalid_report = """# JobFit Analysis Report

## Skills Matrix
| Skill | Match |
|-------|-------|
| Python | ✅ |

## Experience Alignment
Good match.
"""
        mock_client.messages.create.return_value = _make_response(invalid_report)

        with patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_client
            with pytest.raises(SystemExit) as exc_info:
                await analyze_fit(
                    job_text="Job posting",
                    resume_text="Resume text",
                )

        assert exc_info.value.code == EXIT_API
        assert exc_info.value.code == 5
        captured = capsys.readouterr()
        assert "failed to parse" in captured.err.lower()
        assert "match score" in captured.err.lower()

    async def test_malformed_score_exits_5(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Malformed score line should exit with code 5."""
        mock_client = AsyncMock()
        # Response with malformed score line
        invalid_report = """# JobFit Analysis Report

## Overall Match Score: Not a number/10

## Skills Matrix
Test
"""
        mock_client.messages.create.return_value = _make_response(invalid_report)

        with patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_client
            with pytest.raises(SystemExit) as exc_info:
                await analyze_fit(
                    job_text="Job posting",
                    resume_text="Resume text",
                )

        assert exc_info.value.code == EXIT_API
        assert exc_info.value.code == 5
        captured = capsys.readouterr()
        assert "failed to parse" in captured.err.lower()
