"""Pytest configuration for the Tung Tung Sahur submission.

Makes the scored implementation module importable from the test directory
regardless of the working directory used by ``scripts/score.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[1]
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))
