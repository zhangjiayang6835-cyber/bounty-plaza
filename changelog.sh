#!/usr/bin/env bash
# Git Structured Changelog Generator Wrapper
# Resolves claude-builders-bounty/claude-builders-bounty#1 / bounty-plaza#490
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$(which python3 || which python)"

if [[ -z "$PYTHON_BIN" ]]; then
    echo "Error: Python 3 is required to generate changelog." >&2
    exit 1
fi

exec "$PYTHON_BIN" "$SCRIPT_DIR/tools/generate_changelog.py" "$@"
