"""Claude API integration for job-resume fit analysis."""

from __future__ import annotations

import re

import anthropic
from pydantic import BaseModel

from jobfit.errors import EXIT_API, print_error


class AnalysisResult(BaseModel):
    """Result from Claude API job-resume fit analysis."""

    raw_report: str
    score: int
    model: str


async def analyze_fit(
    job_text: str,
    resume_text: str,
    model: str = "claude-sonnet-4-5-20250929",
) -> AnalysisResult:
    """Analyze job-resume fit using Claude API.

    Args:
        job_text: The job posting text.
        resume_text: The resume text.
        model: Claude model to use (default: claude-sonnet-4-5-20250929).

    Returns:
        AnalysisResult with raw markdown report, extracted score, and model used.

    Raises:
        SystemExit: If API call fails (exit code 5).
    """
    # Initialize Anthropic client (auto-reads ANTHROPIC_API_KEY from env)
    try:
        client = anthropic.AsyncAnthropic()
    except Exception as e:
        print_error(
            "failed to initialize Anthropic client",
            detail=str(e),
            hint="Ensure ANTHROPIC_API_KEY environment variable is set",
            exit_code=EXIT_API,
        )

    # Build the prompt
    system_message = """You are an expert job-resume fit analyzer.
Your role is to analyze how well a candidate's resume matches a job posting
and provide actionable insights.

You must produce a detailed markdown report with exactly these sections:
1. Overall Match Score (X/10)
2. Skills Matrix (table format)
3. Experience Alignment
4. Keyword Analysis
5. Culture Fit Notes
6. Suggestions

Be thorough, specific, and constructive in your analysis."""

    user_message = f"""Please analyze the fit between this job posting and resume.

=== JOB POSTING ===
{job_text}

=== RESUME ===
{resume_text}

=== END ===

Provide your analysis in the following format:

# JobFit Analysis Report

## Overall Match Score: X/10

## Skills Matrix
| Skill | Required | You Have | Match |
|-------|----------|----------|-------|
[Fill in with relevant skills]

## Experience Alignment
[Analyze how work history maps to role requirements]

## Keyword Analysis
[Key terms from posting found/missing in resume]

## Culture Fit Notes
[Observations about company culture vs resume tone/experience]

## Suggestions
[Actionable recommendations to improve candidacy]"""

    # Call the API
    try:
        response = await client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_message,
            messages=[
                {
                    "role": "user",
                    "content": user_message,
                }
            ],
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
            "unexpected API error",
            detail=str(e),
            exit_code=EXIT_API,
        )

    # Extract the text from the response
    raw_report = response.content[0].text

    # Extract the score from the report using regex
    score_match = re.search(
        r"##\s*Overall Match Score:\s*(\d+)/10",
        raw_report,
        re.IGNORECASE,
    )
    if score_match:
        score = int(score_match.group(1))
    else:
        # If we can't parse the score, default to 0 and warn
        print_error(
            "failed to parse match score from Claude response",
            detail=(
                "The response did not contain a valid 'Overall Match Score: X/10' line"
            ),
            hint="This may indicate an issue with the API response format",
            exit_code=EXIT_API,
        )

    return AnalysisResult(
        raw_report=raw_report,
        score=score,
        model=model,
    )
