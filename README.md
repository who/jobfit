# JobFit

Analyze how well your resume matches a job posting. JobFit fetches job postings from URLs, parses your resume, and uses Claude AI to generate a detailed compatibility report with match scores, skills analysis, and actionable suggestions.

## Installation

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/who/jobfit.git
cd jobfit
uv sync
uv run playwright install chromium
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

## Usage

```bash
jobfit --url URL --resume RESUME [OPTIONS]
```

### Required arguments

| Flag | Description |
|------|-------------|
| `--url, -u` | URL of the job posting |
| `--resume, -r` | Path to resume file (PDF, DOCX, or TXT) |

### Optional arguments

| Flag | Description |
|------|-------------|
| `--output, -o` | Write report to a file instead of stdout |
| `--quiet, -q` | Suppress progress messages |
| `--verbose, -v` | Show step-by-step progress (default) |
| `--version` | Show version number |

### Examples

```bash
# Basic usage — prints report to stdout
jobfit -u https://example.com/jobs/123 -r resume.pdf

# Save report to a file
jobfit -u https://example.com/jobs/123 -r resume.docx -o report.md

# Quiet mode — no progress output, just the report
jobfit -u https://example.com/jobs/123 -r resume.txt -q > report.md
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
