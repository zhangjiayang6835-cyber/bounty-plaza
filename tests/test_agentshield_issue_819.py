"""
Pytest Test Suite for AgentShield Rules Engine Vulnerabilities (Issue #819)
===========================================================================
Tests reproduction of engine breaks and verifies robust patch logic.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from decimal import Decimal
from scripts.reproduce_agentshield_issue_819 import (
    VulnerableSpendControlEngine,
    PatchedSpendControlEngine,
    extract_date_utc,
    parse_ts,
)


def test_session_decay_tightening_inversion():
    """
    Test Break 1: Session budget decay tightening zero-cap bypass.
    When max_session is $100 and decay_factor is 0.5, remaining budget drops to $0.
    Vulnerable engine approves because `per_call_cap > Decimal('0')` fails.
    Patched engine blocks.
    """
    rules = [{
        "id": "sb1",
        "type": "session_budget",
        "priority": 1,
        "params": {"max_session": 100, "decay_factor": 0.5},
        "action": "BLOCK"
    }]
    priors = [{
        "agent_id": None,
        "amount": 90.0,
        "session_id": "sess_decay",
        "timestamp": "2026-08-10T10:00:00Z"
    }]
    txn = {
        "id": "t_decay",
        "amount": 10.0,
        "merchant": "openai-api",
        "category": "llm_inference",
        "session_id": "sess_decay"
    }

    vuln = VulnerableSpendControlEngine()
    patch = PatchedSpendControlEngine()

    assert vuln.evaluate(txn, rules, priors)["decision"] == "APPROVED"
    assert patch.evaluate(txn, rules, priors)["decision"] == "BLOCKED"


def test_empty_merchant_allowlist_bypass():
    """
    Test Break 2: Empty merchant string bypasses merchant allowlist.
    """
    rules = [{
        "id": "al1",
        "type": "merchant_allowlist",
        "priority": 1,
        "params": {"allowed": ["openai-api", "anthropic-api"]},
        "action": "BLOCK"
    }]
    txn = {
        "id": "t_empty_merchant",
        "amount": 50.0,
        "merchant": "",
        "category": "llm_inference"
    }

    vuln = VulnerableSpendControlEngine()
    patch = PatchedSpendControlEngine()

    assert vuln.evaluate(txn, rules, [])["decision"] == "APPROVED"
    assert patch.evaluate(txn, rules, [])["decision"] == "BLOCKED"


def test_negative_amount_daily_total_bypass():
    """
    Test Break 3: Negative amount bypassing daily total and reducing aggregate spend.
    """
    rules = [{
        "id": "dt1",
        "type": "daily_total",
        "priority": 1,
        "params": {"max_daily": 100},
        "action": "BLOCK"
    }]
    txn = {
        "id": "t_negative",
        "amount": -500.0,
        "merchant": "openai-api",
        "category": "llm_inference",
        "timestamp": "2026-08-10T10:00:00Z"
    }

    vuln = VulnerableSpendControlEngine()
    patch = PatchedSpendControlEngine()

    assert vuln.evaluate(txn, rules, [])["decision"] == "APPROVED"
    assert patch.evaluate(txn, rules, [])["decision"] == "BLOCKED"


def test_timezone_offset_daily_total_evasion():
    """
    Test Break 4: Timezone offset string slice bypasses same-day spend aggregation.
    """
    rules = [{
        "id": "dt2",
        "type": "daily_total",
        "priority": 1,
        "params": {"max_daily": 100},
        "action": "BLOCK"
    }]
    priors = [{
        "agent_id": None,
        "amount": 80.0,
        "timestamp": "2026-08-10T23:00:00-04:00"  # 2026-08-11T03:00:00Z in UTC
    }]
    txn = {
        "id": "t_tz",
        "amount": 80.0,
        "merchant": "openai-api",
        "category": "llm_inference",
        "timestamp": "2026-08-11T03:30:00Z"      # 2026-08-11T03:30:00Z in UTC
    }

    vuln = VulnerableSpendControlEngine()
    patch = PatchedSpendControlEngine()

    assert vuln.evaluate(txn, rules, priors)["decision"] == "APPROVED"
    assert patch.evaluate(txn, rules, priors)["decision"] == "BLOCKED"


def test_utc_date_extraction():
    """
    Verify timezone extraction helper handles varied ISO representations.
    """
    d1 = extract_date_utc("2026-08-10T23:00:00-04:00")
    d2 = extract_date_utc("2026-08-11T03:00:00Z")
    assert d1 == "2026-08-11"
    assert d2 == "2026-08-11"
    assert d1 == d2
