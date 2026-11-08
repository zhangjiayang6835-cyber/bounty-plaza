"""
Root test runner for Issue #137.

Executes all test cases from deliverables.issue_137.test_session_cache.
"""

from __future__ import annotations

import unittest
from deliverables.issue_137.test_session_cache import TestSecureSessionCache

__all__ = ["TestSecureSessionCache"]

if __name__ == "__main__":
    unittest.main()
