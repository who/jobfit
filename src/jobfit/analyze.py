"""Claude API integration for multi-agent job-resume fit analysis."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from pathlib import Path

import anthropic
from pydantic import BaseModel

from jobfit.errors import EXIT_API, print_error

logger = logging.getLogger("jobfit.analyze")

# Directory containing agent persona .md files
AGENTS_DIR = Path(__file__).parent / "agents"


class AgentResult(BaseModel):
    """Result from a single agent's analysis."""

    agent_name: str
    raw_analysis: str
    score: int
    verdict: str | None = None
    strengths: list[str] = []
    concerns: list[str] = []


class AnalysisResult(BaseModel):
    """Result from the multi-agent job-resume fit analysis."""

    raw_report: str
    score: int
    model: str
    agent_results: list[AgentResult] = []


def _load_agent_personas() -> list[tuple[str, str]]:
    """Load all agent persona .md files from the agents directory.

    Returns:
        List of (agent_name, persona_content) tuples.

    Raises:
        SystemExit: If no agent files are found.
    """
    if not AGENTS_DIR.is_dir():
        print_error(
            f"agents directory not found: {AGENTS_DIR}",
            hint="Ensure src/jobfit/agents/ exists with agent persona .md files",
            exit_code=EXIT_API,
        )

    agents = []
    for md_file in sorted(AGENTS_DIR.glob("agent_*.md")):
        content = md_file.read_text(encoding="utf-8")
        # Extract agent name from the first line (e.g., "# Agent: Diana Chen — ...")
        first_line = content.split("\n", 1)[0]
        match = re.match(r"#\s*Agent:\s*(.+?)(?:\s*—|\s*-|\s*$)", first_line)
        name = match.group(1).strip() if match else md_file.stem
        agents.append((name, content))
        logger.debug("Loaded agent persona: %s from %s", name, md_file.name)

    if not agents:
        print_error(
            "no agent persona files found",
            hint=f"Add agent_*.md files to {AGENTS_DIR}",
            exit_code=EXIT_API,
        )

    logger.debug("Loaded %d agent personas", len(agents))
    return agents


def _get_model() -> str:
    """Get the Claude model from CLAUDE_MODEL env var or default.

    Returns:
        Model string to use for API calls.
    """
    return os.environ.get("CLAUDE_MODEL", "claude-opus-4-6")


def _build_user_message(job_text: str, resume_text: str) -> str:
    """Build the user message for agent analysis.

    Args:
        job_text: The job posting text.
        resume_text: The resume text.

    Returns:
        Formatted user message string.
    """
    return f"""Evaluate this candidate's resume against the job posting \
from your specialized perspective.

=== JOB POSTING ===
{job_text}

=== RESUME ===
{resume_text}

=== END ===

Provide your evaluation as follows:

## Analysis
[Your detailed evaluation from your specialized perspective, \
referencing specific evidence from the resume]

## Key Strengths
[Bullet points of strengths relevant to your evaluation focus]

## Concerns
[Bullet points of concerns or red flags from your perspective]

## Verdict
[One-paragraph final assessment]

Finally, provide your structured payload in a JSON code block:

```json
{{
  "score": X,
  "verdict": "your one-paragraph verdict",
  "strengths": ["strength1", "strength2"],
  "concerns": ["concern1", "concern2"]
}}
```

Where score is 1-5 (1=poor fit, 5=excellent fit). This block is machine-parsed."""


async def _run_agent(
    client: anthropic.AsyncAnthropic,
    model: str,
    agent_name: str,
    persona: str,
    job_text: str,
    resume_text: str,
) -> AgentResult:
    """Run a single agent's analysis.

    Args:
        client: The Anthropic async client.
        model: Claude model to use.
        agent_name: Name of the agent.
        persona: Full persona markdown content (used as system prompt).
        job_text: The job posting text.
        resume_text: The resume text.

    Returns:
        AgentResult with the agent's analysis and score.
    """
    user_message = _build_user_message(job_text, resume_text)

    logger.debug("Agent %s: sending request with model=%s", agent_name, model)
    request_start = time.monotonic()

    try:
        response = await client.messages.create(
            model=model,
            max_tokens=4096,
            system=persona,
            messages=[{"role": "user", "content": user_message}],
        )
    except anthropic.AuthenticationError as e:
        print_error(
            "authentication failed",
            detail=str(e),
            hint="Check that your ANTHROPIC_API_KEY is valid",
            exit_code=EXIT_API,
        )
    except anthropic.RateLimitError as e:
        print_error(
            "rate limit exceeded",
            detail=str(e),
            hint="Wait a moment and try again, or upgrade your API plan",
            exit_code=EXIT_API,
        )
    except anthropic.APIStatusError as e:
        print_error(
            "API server error",
            detail=f"Status {e.status_code}: {e.message}",
            hint="The Anthropic API may be experiencing issues. Try again later.",
            exit_code=EXIT_API,
        )
    except anthropic.APIConnectionError as e:
        print_error(
            "API connection error",
            detail=str(e),
            hint="Check your internet connection and try again",
            exit_code=EXIT_API,
        )
    except Exception as e:
        print_error(
            f"unexpected API error for agent {agent_name}",
            detail=str(e),
            exit_code=EXIT_API,
        )

    latency = time.monotonic() - request_start
    raw_analysis = response.content[0].text
    logger.debug(
        "Agent %s: response in %.2fs, stop_reason=%s",
        agent_name,
        latency,
        response.stop_reason,
    )
    if hasattr(response, "usage") and response.usage:
        logger.debug(
            "Agent %s: tokens input=%d, output=%d",
            agent_name,
            response.usage.input_tokens,
            response.usage.output_tokens,
        )

    # Parse structured payload from response — prefer JSON block, fall back to regex
    score = 3  # default if parsing fails
    verdict: str | None = None
    strengths: list[str] = []
    concerns: list[str] = []
    parsed = False

    # Strategy 1: fenced JSON code block — extract last ```json ... ``` and parse
    json_blocks = re.findall(
        r"```json\s*(\{.*?\})\s*```",
        raw_analysis,
        re.DOTALL | re.IGNORECASE,
    )
    if json_blocks:
        try:
            payload = json.loads(json_blocks[-1])
            val = int(payload["score"])
            if 1 <= val <= 5:
                score = val
                verdict = payload.get("verdict")
                strengths = payload.get("strengths", [])
                concerns = payload.get("concerns", [])
                parsed = True
                logger.debug(
                    "Agent %s: parsed score=%d from JSON block", agent_name, score
                )
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            logger.debug("Agent %s: JSON block found but failed to parse", agent_name)

    # Strategy 2: bare JSON object {"score": X} without code fences
    if not parsed:
        bare_json_match = re.search(
            r"(\{[^}]*\"score\"\s*:\s*\d+[^}]*\})",
            raw_analysis,
            re.IGNORECASE,
        )
        if bare_json_match:
            try:
                payload = json.loads(bare_json_match.group(1))
                val = int(payload["score"])
                if 1 <= val <= 5:
                    score = val
                    verdict = payload.get("verdict")
                    strengths = payload.get("strengths", [])
                    concerns = payload.get("concerns", [])
                    parsed = True
                    logger.debug(
                        "Agent %s: parsed score=%d from bare JSON",
                        agent_name,
                        score,
                    )
            except (json.JSONDecodeError, KeyError, ValueError, TypeError):
                logger.debug(
                    "Agent %s: bare JSON found but failed to parse", agent_name
                )

    # Strategy 3: legacy regex fallback (## Score: X/5 variants)
    if not parsed:
        score_patterns = [
            r"##\s*Score:\s*(\d+)\s*/\s*5",
            r"\*{0,2}Score\*{0,2}\s*:?\s*(\d+)\s*/\s*5",
            r"score\s*:?\s*(\d+)\s*/\s*5",
        ]
        for pattern in score_patterns:
            score_match = re.search(pattern, raw_analysis, re.IGNORECASE)
            if score_match:
                val = int(score_match.group(1))
                if 1 <= val <= 5:
                    score = val
                    parsed = True
                    logger.debug(
                        "Agent %s: parsed score=%d with regex pattern=%r",
                        agent_name,
                        score,
                        pattern,
                    )
                    break

    if not parsed:
        logger.debug(
            "Agent %s: could not parse score, using default=%d",
            agent_name,
            score,
        )

    return AgentResult(
        agent_name=agent_name,
        raw_analysis=raw_analysis,
        score=score,
        verdict=verdict,
        strengths=strengths,
        concerns=concerns,
    )


def _aggregate_report(agent_results: list[AgentResult], model: str) -> AnalysisResult:
    """Aggregate individual agent results into a unified report.

    Args:
        agent_results: List of individual agent analysis results.
        model: The model used for analysis.

    Returns:
        AnalysisResult with combined report and composite score.
    """
    # Compute composite score: average of agent scores mapped to 1-10 scale
    if agent_results:
        avg_score = sum(r.score for r in agent_results) / len(agent_results)
        composite_score = round(avg_score * 2)  # Map 1-5 to 2-10
        composite_score = max(1, min(10, composite_score))
    else:
        composite_score = 0

    # Build the combined report
    lines = [
        "# JobFit Analysis Report",
        "",
        f"## Overall Match Score: {composite_score}/10",
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

    # Add summary table
    lines.append("## Score Summary")
    lines.append("")
    lines.append("| Evaluator | Score |")
    lines.append("|-----------|-------|")
    for result in agent_results:
        lines.append(f"| {result.agent_name} | {result.score}/5 |")
    lines.append(f"| **Composite** | **{composite_score}/10** |")
    lines.append("")

    raw_report = "\n".join(lines)

    return AnalysisResult(
        raw_report=raw_report,
        score=composite_score,
        model=model,
        agent_results=agent_results,
    )


async def analyze_fit(
    job_text: str,
    resume_text: str,
    model: str | None = None,
) -> AnalysisResult:
    """Analyze job-resume fit using multiple agent personas concurrently.

    Each agent evaluates the resume from their specialized perspective.
    Results are aggregated into a unified report with a composite score.

    Args:
        job_text: The job posting text.
        resume_text: The resume text.
        model: Claude model to use (overrides CLAUDE_MODEL env var).

    Returns:
        AnalysisResult with combined report, composite score, and per-agent results.

    Raises:
        SystemExit: If API call fails (exit code 5).
    """
    if model is None:
        model = _get_model()

    # Load agent personas
    agents = _load_agent_personas()
    logger.debug("Running %d agents with model=%s", len(agents), model)

    # Initialize Anthropic client
    try:
        client = anthropic.AsyncAnthropic()
    except Exception as e:
        print_error(
            "failed to initialize Anthropic client",
            detail=str(e),
            hint="Ensure ANTHROPIC_API_KEY environment variable is set",
            exit_code=EXIT_API,
        )

    # Run all agents concurrently
    tasks = [
        _run_agent(client, model, name, persona, job_text, resume_text)
        for name, persona in agents
    ]
    agent_results = await asyncio.gather(*tasks)

    # Aggregate results
    result = _aggregate_report(list(agent_results), model)
    logger.debug(
        "Analysis complete: composite_score=%d, agents=%d",
        result.score,
        len(result.agent_results),
    )

    return result
