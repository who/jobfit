# PRD: JobFit CLI - Resume-to-Job Matching Tool

## Metadata
- **Feature ID**: jobfit-5sk
- **Project Type**: CLI
- **Created**: 2026-02-15
- **Author**: Claude (from interview)
- **Interview Confidence**: High
- **Generation Mode**: Full interview

## Overview

### Problem Statement
Job seekers spend significant time manually reading through job postings and trying to assess whether their resume is a good match for a position. This process is tedious, subjective, and error-prone — candidates often miss key requirements or overestimate their fit, leading to wasted applications or missed opportunities. There is no quick, automated way to get an objective assessment of how well a resume aligns with a specific job posting, identify skill gaps, or receive actionable suggestions for improving candidacy.

### Proposed Solution
JobFit is a command-line tool that automates resume-to-job-posting analysis. The user provides a job posting URL and a path to their resume file. The tool fetches the job posting using Playwright with a consumer-style User-Agent to avoid bot detection, parses the resume (supporting PDF, DOCX, and plain text formats), and sends both to Claude's API for detailed analysis. The output is a structured Markdown report covering match score, skills matrix, experience alignment, keyword analysis, culture fit notes, and tailored resume suggestions.

### Success Metrics
- **Analysis accuracy**: Users rate the match assessment as useful/accurate at least 80% of the time (self-reported)
- **Time savings**: Reduces resume-to-job evaluation from ~10 minutes of manual reading to under 60 seconds
- **Completion rate**: 95% of invocations with valid inputs produce a complete report (no crashes or partial output)

## Background & Context
The job search process involves reviewing dozens of postings and tailoring applications. While AI tools exist for resume writing, there is a gap in quick, CLI-based tools that let technically-minded job seekers rapidly assess fit before investing time in a full application. This tool fills that gap by leveraging Claude's language understanding to provide structured, actionable feedback.

## Users & Personas

### Target Users
Job seekers — primarily developers, engineers, and other technical professionals who are comfortable using command-line tools and want a fast, scriptable way to evaluate job postings against their resume.

### User Goals
- Quickly determine if a job posting is worth applying to based on resume fit
- Identify specific skill gaps and missing keywords
- Get actionable suggestions for tailoring their resume to a specific role

### User Environment
- **Operating Systems**: Linux, macOS (primary); Windows via WSL
- **Shell**: bash, zsh
- **Technical Level**: Intermediate to Expert

## Requirements

### Functional Requirements
[P0] FR-001: The CLI shall accept a `--url` flag with a job posting URL and fetch the page content using Playwright with a consumer-style User-Agent header
[P0] FR-002: The CLI shall accept a `--resume` flag with a file path and parse the resume content (supporting PDF, DOCX, and plain text formats)
[P0] FR-003: The CLI shall send the job posting text and resume content to Claude's API and generate a detailed match analysis
[P0] FR-004: The CLI shall output a structured Markdown report to stdout containing: overall match score (1-10), skills matrix, experience alignment, keyword analysis, culture fit notes, and tailored resume suggestions
[P1] FR-005: The CLI shall accept an optional `--output` flag to write the report to a file instead of stdout
[P0] FR-006: The CLI shall read the Anthropic API key from the `ANTHROPIC_API_KEY` environment variable and fail with a clear error if not set
[P1] FR-007: The CLI shall display verbose step-by-step progress messages to stderr during fetching and analysis

### Non-Functional Requirements
[P0] NFR-001: The CLI shall provide clear, actionable error messages for all failure modes (missing API key, invalid URL, unreadable resume, network errors, unsupported file format)
[P0] NFR-002: The CLI shall complete the full fetch-and-analyze pipeline within 120 seconds for typical job postings
[P1] NFR-003: The CLI shall gracefully handle pages that cannot be fetched (login walls, CAPTCHAs, timeouts) with descriptive error messages
[P1] NFR-004: The CLI shall respect the `NO_COLOR` environment variable for progress output
[P2] NFR-005: The CLI shall support `--help` and `--version` flags

## CLI Design

### Command Structure

```
jobfit --url <url> --resume <path> [--output <path>] [--verbose] [--help] [--version]
```

This is a flat, single-command tool with no subcommands.

### Flags

| Flag | Short | Type | Default | Required | Description |
|------|-------|------|---------|----------|-------------|
| --url | -u | string | — | Yes | URL of the job posting to analyze |
| --resume | -r | string | — | Yes | Path to resume file (PDF, DOCX, or TXT) |
| --output | -o | string | — | No | Write report to file instead of stdout |
| --verbose | -v | bool | true | No | Show step-by-step progress on stderr |
| --quiet | -q | bool | false | No | Suppress progress messages |
| --help | -h | bool | false | No | Show help information |
| --version | | bool | false | No | Show version number |

### Input Sources

| Source | Support | Notes |
|--------|---------|-------|
| Command-line flags | Yes | Primary input method (`--url`, `--resume`) |
| Standard input (stdin) | No | Not supported in v1 |
| File input | Yes | Resume file via `--resume` flag |
| Environment variables | Yes | `ANTHROPIC_API_KEY` for API authentication |
| Config file | No | Not supported in v1 |

### Output Format

#### Markdown Report (stdout or `--output` file)
```markdown
# JobFit Analysis Report

## Overall Match Score: 7/10

## Skills Matrix
| Skill | Required | You Have | Match |
|-------|----------|----------|-------|
| Python | Yes | Yes | ✅ |
| Kubernetes | Yes | No | ❌ |
| ...

## Experience Alignment
- [Analysis of how work history maps to role requirements]

## Keyword Analysis
- [Key terms from posting found/missing in resume]

## Culture Fit Notes
- [Observations about company culture vs resume tone/experience]

## Suggestions
- [Actionable recommendations to improve candidacy]
```

#### Progress Output (stderr)
```
Fetching job posting from https://example.com/job/123...
Successfully fetched job posting (2,450 words)
Reading resume from ./resume.pdf...
Parsed resume (1,200 words, PDF format)
Sending to Claude for analysis...
Analysis complete. Generating report...
```

### Exit Codes

| Code | Meaning | When |
|------|---------|------|
| 0 | Success | Report generated successfully |
| 1 | General error | Unspecified error occurred |
| 2 | Usage error | Missing required flags or invalid flag values |
| 3 | Input error | Resume file not found, unreadable, or unsupported format |
| 4 | Network error | Failed to fetch job posting (timeout, DNS, HTTP error) |
| 5 | API error | Claude API failure (missing key, rate limit, server error) |
| 6 | Parse error | Could not extract meaningful content from job posting page |

### Error Messages

**Format**:
```
error: [brief description]

  [detailed explanation]

hint: [suggestion for fixing]
```

**Examples**:
```
error: ANTHROPIC_API_KEY environment variable not set

hint: export ANTHROPIC_API_KEY=sk-ant-...
```

```
error: could not fetch job posting from https://example.com/job/123

  the page returned a 403 status code, which may indicate bot detection or a login wall

hint: try opening the URL in a browser to verify it's publicly accessible
```

```
error: unsupported resume format: .rtf

  supported formats: .pdf, .docx, .txt

hint: convert your resume to PDF or plain text and try again
```

## System Architecture

### Components
- **CLI Parser**: `argparse` or `click` for argument parsing
- **Page Fetcher**: Playwright with consumer-style User-Agent for fetching job postings
- **Resume Parser**: PDF (PyMuPDF or pdfplumber), DOCX (python-docx), plain text (built-in)
- **AI Analyzer**: Anthropic Python SDK for Claude API calls
- **Report Generator**: Formats Claude's analysis into structured Markdown

### Dependencies
- `playwright` — Browser automation for fetching job postings
- `anthropic` — Claude API client
- `pymupdf` or `pdfplumber` — PDF parsing
- `python-docx` — DOCX parsing
- `click` or `argparse` — CLI framework (argparse is stdlib)
- `rich` — (optional) for colored/styled progress output

## Milestones & Phases

### Phase 1: Foundation
**Goal**: Basic CLI structure with argument parsing and resume reading
**Deliverables**:
- Project setup with uv, pyproject.toml
- Argument parsing with --url, --resume, --output, --help, --version
- Resume file reading (PDF, DOCX, TXT)
- Error handling for invalid inputs

### Phase 2: Core Pipeline
**Goal**: End-to-end fetch, analyze, and report
**Deliverables**:
- Playwright-based job posting fetcher with consumer User-Agent
- Claude API integration for match analysis
- Markdown report generation
- Verbose progress logging to stderr

### Phase 3: Polish
**Goal**: Production-ready tool
**Deliverables**:
- Comprehensive error handling for all failure modes
- Exit codes per specification
- `--output` file writing
- Installation via `uv tool install`

## Epic Breakdown

### Epic: Project Setup & CLI Framework
- **Requirements Covered**: FR-006, NFR-005
- **Tasks**:
  - Set up project structure with uv and pyproject.toml
  - Implement argument parsing (--url, --resume, --output, --help, --version)
  - Validate ANTHROPIC_API_KEY environment variable
  - Define exit codes and error message formatting

### Epic: Resume Parsing
- **Requirements Covered**: FR-002
- **Tasks**:
  - Implement PDF resume parsing
  - Implement DOCX resume parsing
  - Implement plain text resume reading
  - Add format detection and validation

### Epic: Job Posting Fetching
- **Requirements Covered**: FR-001, NFR-003
- **Tasks**:
  - Set up Playwright with consumer User-Agent
  - Implement page fetching with timeout handling
  - Extract meaningful text content from HTML
  - Handle error cases (login walls, CAPTCHAs, network failures)

### Epic: AI Analysis & Report
- **Requirements Covered**: FR-003, FR-004, FR-005, FR-007
- **Tasks**:
  - Implement Claude API integration with structured prompt
  - Design and implement Markdown report template
  - Add verbose progress logging to stderr
  - Implement --output file writing

## Out of Scope
- Batch processing of multiple job URLs
- Interactive/TUI mode
- Resume editing or rewriting
- Job posting search/discovery
- Shell completion generation
- Config file support
- JSON/YAML output formats
- Caching of previous analyses
- Resume format conversion

## Open Questions
- Which PDF parsing library to use (PyMuPDF vs pdfplumber) — choose based on extraction quality during implementation
- Which Claude model to default to (Sonnet for speed/cost vs Opus for quality) — can be decided during implementation

## Appendix

### Similar Tools
- **resumeworded.com**: Web-based resume scorer, but not CLI and requires account
- **jobscan.co**: Web-based ATS optimization, but not open source or CLI-based
- **JobFit differs**: Fully local CLI tool, uses state-of-the-art AI, outputs structured Markdown, no account required
