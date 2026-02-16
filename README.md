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

JobFit requires an [Anthropic API key](https://console.anthropic.com/):

```bash
export ANTHROPIC_API_KEY='sk-ant-...'
```

Or create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Optionally, set a default resume path:

```bash
export RESUME_PATH=/path/to/resume.pdf
```

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

# Save report to a file
uv run jobfit -j posting.pdf -r resume.docx -o report.md

# Using RESUME_PATH env var (no --resume needed)
export RESUME_PATH=resume.pdf
uv run jobfit -j posting.pdf

# Quiet mode — no progress output, just the report
uv run jobfit -j posting.txt -r resume.pdf -q > report.md
```

## Output

JobFit generates a Markdown report containing:

- **Overall Match Score** (1–10)
- **Skills Matrix** — comparison of required vs. your skills
- **Experience Alignment** — how your work history maps to the role
- **Keyword Analysis** — key terms found or missing in your resume
- **Culture Fit Notes** — observations on company culture alignment
- **Suggestions** — actionable recommendations to improve your fit

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
