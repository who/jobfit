# JobFit

Analyze how well your resume matches a job posting. JobFit parses job posting files and your resume, then uses Claude AI to generate a detailed compatibility report with match scores, skills analysis, and actionable suggestions.

## Installation

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/who/jobfit.git
cd jobfit
uv sync
```

## Configuration

JobFit requires an [Anthropic API key](https://console.anthropic.com/) and the path to your resume.

### Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key |
| `RESUME_PATH` | No | Default path to your resume file (PDF, DOCX, or TXT) |
| `CLAUDE_MODEL` | No | Override the Claude model (defaults to `claude-opus-4-6`) |

Set them in your shell:

```bash
export ANTHROPIC_API_KEY='sk-ant-...'
export RESUME_PATH=/path/to/resume.pdf
```

Or create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
RESUME_PATH=/path/to/resume.pdf
```

The `.env` file is loaded automatically at startup. If `RESUME_PATH` is set, you can omit the `--resume` flag when running JobFit.

## Usage

```bash
uv run jobfit --job FILE [--resume FILE] [OPTIONS]
```

### Required arguments

| Flag | Description |
|------|-------------|
| `--job, -j` | Path to job posting file (PDF, TXT, or MD) |

### Optional arguments

| Flag | Description |
|------|-------------|
| `--resume, -r` | Path to resume file (PDF, DOCX, or TXT). Defaults to `RESUME_PATH` env var |
| `--output, -o` | Write report to a file instead of stdout |
| `--quiet, -q` | Suppress progress messages |
| `--verbose, -v` | Enable debug logging |
| `--version` | Show version number |

### Examples

```bash
# Basic usage — prints report to stdout
uv run jobfit -j posting.pdf -r resume.pdf

# Save report to a file (defaults to <job-stem>-jobfit-results.md)
uv run jobfit -j posting.pdf -r resume.docx -o report.md

# Using RESUME_PATH env var (no --resume needed)
export RESUME_PATH=resume.pdf
uv run jobfit -j posting.pdf

# Quiet mode — no progress output, just the report
uv run jobfit -j posting.txt -r resume.pdf -q > report.md

# Using the shell wrapper (verbose mode, output defaults automatically)
./jobfit.sh posting.pdf
```

## Output

JobFit generates a Markdown report containing:

- **Overall Match Score** (1–10)
- **Skills Matrix** — comparison of required vs. your skills
- **Experience Alignment** — how your work history maps to the role
- **Keyword Analysis** — key terms found or missing in your resume
- **Culture Fit Notes** — observations on company culture alignment
- **Suggestions** — actionable recommendations to improve your fit

## Adding a New Agent

JobFit uses a multi-agent evaluation system. Each agent is a Markdown file in `src/jobfit/agents/` that defines a specialist persona. Agents are **auto-discovered** at runtime — no code changes needed.

To add a new agent:

1. Create a new `.md` file in `src/jobfit/agents/` (e.g., `agent_culture_fit.md`). Files starting with `_` are ignored.
2. Start the file with a header line matching this format:
   ```
   # Agent: Your Agent Name
   ```
3. Define the agent's persona below the header — its evaluation focus, scoring rubric (1–5), red flags, and any domain-specific guidance.

The shared response format from `_response_format.md` is appended to every agent automatically, so you don't need to repeat output formatting instructions.

**Current agents:**

| File | Focus Area |
|------|------------|
| `agent_execution_delivery.md` | Execution & Delivery |
| `agent_growth_trajectory.md` | Growth Trajectory |
| `agent_people_leadership.md` | People Leadership |
| `agent_strategic_vision.md` | Strategic Vision |
| `agent_technical_depth.md` | Technical Depth |

## Ortus Automation

This project was scaffolded with [Ortus](https://github.com/who/ortus), which provides AI-powered development workflows including PRD-to-issues decomposition and automated implementation loops. See the `ortus/` directory for scripts and prompts.

## Development

```bash
uv run pytest              # Run tests
uv run ruff check .        # Lint
uv run ruff format .       # Format
```

## Tech Stack

- **Language**: Python 3.11+
- **Package Manager**: uv
- **Linter**: ruff
- **License**: MIT
