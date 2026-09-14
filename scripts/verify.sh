#!/usr/bin/env bash
# NIO-22 / issue-819 verify: bounty repro tests + eval gym (agentshield-spend 1.0.1).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

PYTHON="${ROOT}/.venv/bin/python"
PIP="${ROOT}/.venv/bin/pip"

if [[ ! -x "${PYTHON}" ]]; then
  python3 -m venv "${ROOT}/.venv"
fi

"${PIP}" install -q -r requirements-dev.txt

"${PYTHON}" -m pytest -q
"${PYTHON}" -m tests.agentshield_eval_gym_bounty
