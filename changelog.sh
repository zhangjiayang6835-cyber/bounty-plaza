#!/usr/bin/env bash
# changelog.sh - Automatically generates a structured CHANGELOG.md from git history
# Resolves Issue #504: [BOUNTY $50] SKILL: Generate a structured CHANGELOG from git

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

OUTPUT_FILE="${1:-CHANGELOG.md}"
VERSION="${2:-Unreleased}"

echo "Generating structured changelog to ${OUTPUT_FILE}..."
"${PYTHON_BIN}" "${SCRIPT_DIR}/scripts/generate_changelog.py"

echo "Changelog generated successfully."
