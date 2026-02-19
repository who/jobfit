#!/usr/bin/env bash
set -euo pipefail

# --- Color support ---
if [[ -t 1 ]] && command -v tput &>/dev/null && [[ $(tput colors 2>/dev/null || echo 0) -ge 8 ]]; then
  RED=$(tput setaf 1)
  GREEN=$(tput setaf 2)
  YELLOW=$(tput setaf 3)
  BOLD=$(tput bold)
  RESET=$(tput sgr0)
else
  RED="" GREEN="" YELLOW="" BOLD="" RESET=""
fi

pass()  { printf "${GREEN}✓${RESET} %s\n" "$1"; }
fail()  { printf "${RED}✗${RESET} %s\n" "$1"; }
warn()  { printf "${YELLOW}!${RESET} %s\n" "$1"; }
info()  { printf "  %s\n" "$1"; }

# --- Checks ---

# 1. Job description argument
if [[ $# -lt 1 || -z "${1:-}" ]]; then
  fail "No job description provided"
  info "Usage: ${BOLD}./jobfit.sh <job-description-file>${RESET}"
  info "Example: ./jobfit.sh job_posting.txt"
  exit 1
fi
pass "Job description argument provided"

# 2. uv
if ! command -v uv &>/dev/null; then
  fail "uv is not installed or not on PATH"
  info "Install uv: ${BOLD}https://docs.astral.sh/uv/getting-started/installation/${RESET}"
  exit 1
fi
pass "uv found ($(uv --version))"

# 3. Python >=3.11
python_version=$(uv run python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || true)
if [[ -z "$python_version" ]]; then
  fail "Could not determine Python version"
  info "Ensure Python >=3.11 is available"
  exit 1
fi
major=${python_version%%.*}
minor=${python_version#*.}
if [[ "$major" -lt 3 ]] || { [[ "$major" -eq 3 ]] && [[ "$minor" -lt 11 ]]; }; then
  fail "Python $python_version found, but >=3.11 is required"
  info "Install Python 3.11+: ${BOLD}https://www.python.org/downloads/${RESET}"
  exit 1
fi
pass "Python $python_version meets minimum (>=3.11)"

# 4. ANTHROPIC_API_KEY
if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  fail "ANTHROPIC_API_KEY environment variable is not set"
  info "Set it with: ${BOLD}export ANTHROPIC_API_KEY='sk-ant-...'${RESET}"
  exit 1
fi
pass "ANTHROPIC_API_KEY is set"

# 5. Dependencies installed (.venv exists)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ ! -d "$SCRIPT_DIR/.venv" ]]; then
  fail "Dependencies not installed (.venv not found)"
  info "Run: ${BOLD}uv sync${RESET}"
  exit 1
fi
pass "Dependencies installed (.venv found)"

# --- Run ---
printf "\n${GREEN}All checks passed.${RESET} Running jobfit...\n\n"
uv run jobfit -v -j "$1"
