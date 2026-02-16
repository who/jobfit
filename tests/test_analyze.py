"""Tests for multi-agent Claude API job-resume fit analysis."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import pytest

from jobfit.analyze import (
    AgentResult,
    AnalysisResult,
    _aggregate_report,
    _build_user_message,
    _load_agent_personas,
    _run_agent,
    analyze_fit,
)
from jobfit.errors import EXIT_API


def _make_response(text: str) -> MagicMock:
    """Create a mock API response with the given text content."""
    content_block = MagicMock()
    content_block.text = text
    response = MagicMock()
    response.content = [content_block]
    response.stop_reason = "end_turn"
    response.usage = MagicMock()
    response.usage.input_tokens = 100
    response.usage.output_tokens = 200
    return response


def _make_agent_response(score: int = 4) -> str:
    """Create a valid agent analysis response."""
    return f"""## Analysis
Strong technical background with relevant experience.

## Key Strengths
- Excellent Python skills
- Leadership experience

## Concerns
- Limited cloud experience

## Verdict
A strong candidate overall.

```json
{{
  "score": {score},
  "verdict": "A strong candidate overall.",
  "strengths": ["Excellent Python skills", "Leadership experience"],
  "concerns": ["Limited cloud experience"]
}}
```"""


class TestAgentResult:
    """Tests for AgentResult Pydantic model."""

    def test_valid_construction(self) -> None:
        result = AgentResult(
            agent_name="Diana Chen",
            raw_analysis="test analysis",
            score=4,
        )
        assert result.agent_name == "Diana Chen"
        assert result.score == 4

    def test_optional_fields_defaults(self) -> None:
        result = AgentResult(
            agent_name="Test",
            raw_analysis="test",
            score=3,
        )
        assert result.verdict is None
        assert result.strengths == []
        assert result.concerns == []

    def test_structured_fields(self) -> None:
        result = AgentResult(
            agent_name="Test",
            raw_analysis="test",
            score=4,
            verdict="Strong candidate.",
            strengths=["Python", "Leadership"],
            concerns=["Cloud experience"],
        )
        assert result.verdict == "Strong candidate."
        assert result.strengths == ["Python", "Leadership"]
        assert result.concerns == ["Cloud experience"]


class TestAnalysisResult:
    """Tests for AnalysisResult Pydantic model."""

    def test_valid_construction(self) -> None:
        result = AnalysisResult(
            raw_report="# Report",
            score=8,
            model="claude-opus-4-6",
        )
        assert result.raw_report == "# Report"
        assert result.score == 8
        assert result.model == "claude-opus-4-6"
        assert result.agent_results == []

    def test_with_agent_results(self) -> None:
        agent = AgentResult(agent_name="Test", raw_analysis="analysis", score=3)
        result = AnalysisResult(
            raw_report="# Report",
            score=6,
            model="test-model",
            agent_results=[agent],
        )
        assert len(result.agent_results) == 1
        assert result.agent_results[0].agent_name == "Test"


class TestLoadAgentPersonas:
    """Tests for loading agent persona files."""

    def test_loads_all_five_agents(self) -> None:
        agents = _load_agent_personas()
        assert len(agents) == 5

    def test_agent_names_extracted(self) -> None:
        agents = _load_agent_personas()
        names = [name for name, _ in agents]
        assert "Diana Chen" in names
        assert "Marcus Webb" in names
        assert "James Okafor" in names
        assert "Priya Ramaswamy" in names
        assert "Sofia Engström" in names

    def test_agent_content_not_empty(self) -> None:
        agents = _load_agent_personas()
        for name, content in agents:
            assert len(content) > 100, f"Agent {name} content seems too short"


class TestBuildUserMessage:
    """Tests for user message construction."""

    def test_contains_job_and_resume(self) -> None:
        msg = _build_user_message("Job posting text", "Resume text here")
        assert "Job posting text" in msg
        assert "Resume text here" in msg

    def test_contains_delimiters(self) -> None:
        msg = _build_user_message("job", "resume")
        assert "=== JOB POSTING ===" in msg
        assert "=== RESUME ===" in msg
        assert "=== END ===" in msg

    def test_requests_json_payload_format(self) -> None:
        msg = _build_user_message("job", "resume")
        assert '"score": X' in msg
        assert '"verdict"' in msg
        assert '"strengths"' in msg
        assert '"concerns"' in msg
        assert "machine-parsed" in msg


class TestAggregateReport:
    """Tests for report aggregation."""

    def test_composite_score_mapping(self) -> None:
        """Agent scores (1-5) should map to composite score (1-10)."""
        results = [
            AgentResult(agent_name="A", raw_analysis="a", score=5),
            AgentResult(agent_name="B", raw_analysis="b", score=5),
        ]
        analysis = _aggregate_report(results, "test-model")
        assert analysis.score == 10  # avg 5.0 * 2 = 10

    def test_composite_score_rounding(self) -> None:
        results = [
            AgentResult(agent_name="A", raw_analysis="a", score=3),
            AgentResult(agent_name="B", raw_analysis="b", score=4),
        ]
        analysis = _aggregate_report(results, "test-model")
        assert analysis.score == 7  # avg 3.5 * 2 = 7

    def test_composite_score_clamped(self) -> None:
        results = [
            AgentResult(agent_name="A", raw_analysis="a", score=1),
        ]
        analysis = _aggregate_report(results, "test-model")
        assert analysis.score == 2  # avg 1.0 * 2 = 2, min 1

    def test_report_contains_agent_sections(self) -> None:
        results = [
            AgentResult(agent_name="Diana Chen", raw_analysis="tech analysis", score=4),
            AgentResult(
                agent_name="Marcus Webb",
                raw_analysis="people analysis",
                score=3,
            ),
        ]
        analysis = _aggregate_report(results, "test-model")
        assert "Diana Chen" in analysis.raw_report
        assert "Marcus Webb" in analysis.raw_report
        assert "tech analysis" in analysis.raw_report
        assert "people analysis" in analysis.raw_report

    def test_report_has_score_summary_table(self) -> None:
        results = [
            AgentResult(agent_name="Agent A", raw_analysis="a", score=4),
            AgentResult(agent_name="Agent B", raw_analysis="b", score=3),
        ]
        analysis = _aggregate_report(results, "test-model")
        assert "## Score Summary" in analysis.raw_report
        assert "| Evaluator | Score |" in analysis.raw_report
        assert "| Agent A | 4/5 |" in analysis.raw_report
        assert "| Agent B | 3/5 |" in analysis.raw_report

    def test_report_has_overall_score(self) -> None:
        results = [
            AgentResult(agent_name="A", raw_analysis="a", score=4),
        ]
        analysis = _aggregate_report(results, "test-model")
        assert "## Overall Match Score: 8/10" in analysis.raw_report

    def test_empty_results(self) -> None:
        analysis = _aggregate_report([], "test-model")
        assert analysis.score == 0


class TestAnalyzeFitSuccess:
    """Tests for successful multi-agent API calls."""

    async def test_returns_analysis_result(self) -> None:
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = _make_response(
            _make_agent_response(4)
        )

        with patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_client
            result = await analyze_fit(
                job_text="Senior Python Developer needed",
                resume_text="Python developer with 5 years experience",
                model="test-model",
            )

        assert isinstance(result, AnalysisResult)
        assert result.model == "test-model"
        assert len(result.agent_results) == 5
        assert "JobFit Analysis Report" in result.raw_report

    async def test_model_from_env_var(self) -> None:
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = _make_response(
            _make_agent_response(3)
        )

        with (
            patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic,
            patch.dict("os.environ", {"CLAUDE_MODEL": "claude-sonnet-4-5-20250929"}),
        ):
            mock_anthropic.return_value = mock_client
            result = await analyze_fit(
                job_text="Job posting",
                resume_text="Resume text",
            )

        assert result.model == "claude-sonnet-4-5-20250929"

    async def test_default_model(self) -> None:
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = _make_response(
            _make_agent_response(3)
        )

        with (
            patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic,
            patch.dict("os.environ", {}, clear=True),
        ):
            mock_anthropic.return_value = mock_client
            result = await analyze_fit(
                job_text="Job posting",
                resume_text="Resume text",
            )

        assert result.model == "claude-opus-4-6"

    async def test_explicit_model_overrides_env(self) -> None:
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = _make_response(
            _make_agent_response(3)
        )

        with (
            patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic,
            patch.dict("os.environ", {"CLAUDE_MODEL": "env-model"}),
        ):
            mock_anthropic.return_value = mock_client
            result = await analyze_fit(
                job_text="Job posting",
                resume_text="Resume text",
                model="explicit-model",
            )

        assert result.model == "explicit-model"

    async def test_all_agents_called_concurrently(self) -> None:
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = _make_response(
            _make_agent_response(4)
        )

        with patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_client
            await analyze_fit(
                job_text="Job posting",
                resume_text="Resume text",
                model="test-model",
            )

        # Should have called the API 5 times (once per agent)
        assert mock_client.messages.create.call_count == 5
        # Each call should use agent persona as system prompt
        for call in mock_client.messages.create.call_args_list:
            assert "system" in call.kwargs
            assert len(call.kwargs["system"]) > 0

    async def test_agent_scores_parsed(self) -> None:
        mock_client = AsyncMock()
        # Return different scores for each call
        scores = [5, 4, 3, 4, 5]
        mock_client.messages.create.side_effect = [
            _make_response(_make_agent_response(s)) for s in scores
        ]

        with patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_client
            result = await analyze_fit(
                job_text="Job",
                resume_text="Resume",
                model="test-model",
            )

        agent_scores = [r.score for r in result.agent_results]
        assert agent_scores == scores


class TestAnalyzeFitErrors:
    """Tests for API error handling."""

    async def test_authentication_error_exits_5(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_client.messages.create.side_effect = anthropic.AuthenticationError(
            "Invalid API key",
            response=mock_response,
            body=None,
        )

        with pytest.raises(SystemExit) as exc_info:
            await _run_agent(
                client=mock_client,
                model="test-model",
                agent_name="Test Agent",
                persona="Test persona",
                job_text="Job posting",
                resume_text="Resume text",
            )

        assert exc_info.value.code == EXIT_API
        captured = capsys.readouterr()
        assert "authentication" in captured.err.lower()

    async def test_rate_limit_error_exits_5(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_client.messages.create.side_effect = anthropic.RateLimitError(
            "Rate limit exceeded",
            response=mock_response,
            body=None,
        )

        with pytest.raises(SystemExit) as exc_info:
            await _run_agent(
                client=mock_client,
                model="test-model",
                agent_name="Test Agent",
                persona="Test persona",
                job_text="Job posting",
                resume_text="Resume text",
            )

        assert exc_info.value.code == EXIT_API
        captured = capsys.readouterr()
        assert "rate limit" in captured.err.lower()

    async def test_client_init_error_exits_5(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        with patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_anthropic.side_effect = Exception("Missing API key")
            with pytest.raises(SystemExit) as exc_info:
                await analyze_fit(
                    job_text="Job posting",
                    resume_text="Resume text",
                    model="test-model",
                )

        assert exc_info.value.code == EXIT_API
        captured = capsys.readouterr()
        assert "failed to initialize" in captured.err.lower()


class TestScoreParsing:
    """Tests for agent score extraction from API response."""

    async def test_parses_standard_format(self) -> None:
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = _make_response(
            "## Score: 4/5\n\nGood candidate."
        )

        with patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_client
            result = await analyze_fit(
                job_text="Job", resume_text="Resume", model="test-model"
            )

        # All 5 agents get the same response, so all should parse score=4
        for agent_result in result.agent_results:
            assert agent_result.score == 4

    async def test_defaults_to_3_on_missing_score(self) -> None:
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = _make_response(
            "No score in this response.\nJust some analysis text."
        )

        with patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_client
            result = await analyze_fit(
                job_text="Job", resume_text="Resume", model="test-model"
            )

        for agent_result in result.agent_results:
            assert agent_result.score == 3

    async def test_rejects_out_of_range_score(self) -> None:
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = _make_response(
            "## Score: 9/5\n\nInvalid score."
        )

        with patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_client
            result = await analyze_fit(
                job_text="Job", resume_text="Resume", model="test-model"
            )

        # 9 is out of 1-5 range, should default to 3
        for agent_result in result.agent_results:
            assert agent_result.score == 3

    async def test_parses_json_block_format(self) -> None:
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = _make_response(
            '## Analysis\nGreat fit.\n\n```json\n{"score": 5}\n```'
        )

        with patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_client
            result = await analyze_fit(
                job_text="Job", resume_text="Resume", model="test-model"
            )

        for agent_result in result.agent_results:
            assert agent_result.score == 5

    async def test_parses_full_json_payload(self) -> None:
        """JSON block with verdict/strengths/concerns should populate AgentResult."""
        mock_client = AsyncMock()
        payload = (
            '```json\n{"score": 4, "verdict": "Solid fit.", '
            '"strengths": ["Python", "AWS"], "concerns": ["No Go"]}\n```'
        )
        mock_client.messages.create.return_value = _make_response(
            f"## Analysis\nGood.\n\n{payload}"
        )

        with patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_client
            result = await analyze_fit(
                job_text="Job", resume_text="Resume", model="test-model"
            )

        for agent_result in result.agent_results:
            assert agent_result.score == 4
            assert agent_result.verdict == "Solid fit."
            assert agent_result.strengths == ["Python", "AWS"]
            assert agent_result.concerns == ["No Go"]

    async def test_parses_bare_json_format(self) -> None:
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = _make_response(
            '## Analysis\nDecent candidate.\n\n{"score": 2}'
        )

        with patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_client
            result = await analyze_fit(
                job_text="Job", resume_text="Resume", model="test-model"
            )

        for agent_result in result.agent_results:
            assert agent_result.score == 2

    async def test_json_score_preferred_over_regex(self) -> None:
        """JSON block score should take priority over markdown score."""
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = _make_response(
            '## Score: 2/5\n\nAnalysis here.\n\n```json\n{"score": 4}\n```'
        )

        with patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_client
            result = await analyze_fit(
                job_text="Job", resume_text="Resume", model="test-model"
            )

        for agent_result in result.agent_results:
            assert agent_result.score == 4

    async def test_legacy_regex_still_works(self) -> None:
        """Old ## Score: X/5 format should still parse as fallback."""
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = _make_response(
            "## Score: 4/5\n\nGood candidate with strong skills."
        )

        with patch("jobfit.analyze.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_client
            result = await analyze_fit(
                job_text="Job", resume_text="Resume", model="test-model"
            )

        for agent_result in result.agent_results:
            assert agent_result.score == 4
