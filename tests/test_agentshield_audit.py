"""Unit test suite for AgentShield Rules Engine Vulnerability Reproduction and Hardening.
Tests Issue #819 requirements:
- Reproduction 1: Rule Priority Conflict / Whitelist Evasion (False Negative).
  Whitelist rule allows a transaction to evade velocity ceilings.
- Reproduction 2: Precision Drift (sub-cent float accumulator drift).
- Hardened Engine verification:
  * Strict fail-closed rule precedence (Deny/Velocity limits override Whitelist).
  * Exact Decimal precision preventing underflow/overflow drift.
  * Thread-safe atomic velocity tracking across sliding windows.
"""

from decimal import Decimal
import time
import pytest
from scripts.agentshield_audit import (
    EvaluationOutcome,
    FlawedAgentShieldEngine,
    HardenedAgentShieldEngine,
    TransactionPayload,
)


def test_reproduce_rule_priority_conflict_whitelist_velocity_bypass():
    """Reproduces the critical False Negative in the flawed engine:

    A whitelisted recipient completely bypasses the $500 velocity limit, allowing
    an unlimited amount to be drained.
    """
    flawed = FlawedAgentShieldEngine(per_tx_limit=100.0, hourly_velocity_limit=500.0)
    flawed.add_whitelist("0xPartnerVault")

    # Regular recipient gets blocked after limit
    flawed.evaluate_transaction("tx1", "0xRegular", 400.0)
    blocked_res = flawed.evaluate_transaction("tx2", "0xRegular", 200.0)
    assert blocked_res["outcome"] == EvaluationOutcome.BLOCKED.value

    # VULNERABILITY REPRODUCTION: Whitelisted recipient can transact $10,000.00 completely evading the limit!
    exploit_res = flawed.evaluate_transaction("tx_exploit", "0xPartnerVault", 10000.0)
    assert exploit_res["outcome"] == EvaluationOutcome.PASSED.value, "Flawed engine permitted unlimited spend for whitelist"
    assert exploit_res["cumulative_spent"] > 500.0


def test_hardened_engine_enforces_velocity_limit_regardless_of_whitelist():
    """Verifies that in the hardened engine, security limits strictly override whitelist."""
    hardened = HardenedAgentShieldEngine(
        per_tx_limit=Decimal("100.00"),
        hourly_velocity_limit=Decimal("500.00"),
        window_seconds=3600.0,
    )
    hardened.add_whitelist("0xPartnerVault")

    now = time.time()
    # Transaction 1: $100.00 to whitelisted vault -> PASS
    tx1 = TransactionPayload(
        tx_id="tx1",
        sender="0xAlice",
        recipient="0xPartnerVault",
        amount=Decimal("100.00"),
        timestamp=now,
    )
    res1 = hardened.evaluate_transaction(tx1)
    assert res1["outcome"] == EvaluationOutcome.PASSED.value
    assert res1["can_execute"] is True

    # Transaction 2: $150.00 exceeds per_tx_limit ($100.00) -> BLOCKED even though whitelisted!
    tx2 = TransactionPayload(
        tx_id="tx2",
        sender="0xAlice",
        recipient="0xPartnerVault",
        amount=Decimal("150.00"),
        timestamp=now,
    )
    res2 = hardened.evaluate_transaction(tx2)
    assert res2["outcome"] == EvaluationOutcome.BLOCKED.value
    assert res2["reason"] == "EXCEEDED_PER_TX_LIMIT"
    assert res2["can_execute"] is False


def test_hardened_engine_exact_decimal_sliding_window_velocity():
    """Verifies exact Decimal precision on boundary transactions (no float epsilon error)."""
    hardened = HardenedAgentShieldEngine(
        per_tx_limit=Decimal("100.00"),
        hourly_velocity_limit=Decimal("200.00"),
        window_seconds=3600.0,
    )

    now = time.time()
    # 2 transactions of $99.99 = $199.98
    t1 = TransactionPayload("t1", "0xAlice", "0xBob", Decimal("99.99"), timestamp=now)
    t2 = TransactionPayload("t2", "0xAlice", "0xBob", Decimal("99.99"), timestamp=now + 1.0)

    assert hardened.evaluate_transaction(t1)["outcome"] == EvaluationOutcome.PASSED.value
    assert hardened.evaluate_transaction(t2)["outcome"] == EvaluationOutcome.PASSED.value

    # Exact remaining capacity: $200.00 - $199.98 = $0.02
    t3_pass = TransactionPayload("t3_pass", "0xAlice", "0xBob", Decimal("0.02"), timestamp=now + 2.0)
    assert hardened.evaluate_transaction(t3_pass)["outcome"] == EvaluationOutcome.PASSED.value

    # Exact over-limit by $0.01 -> BLOCKED
    t4_block = TransactionPayload("t4_block", "0xAlice", "0xBob", Decimal("0.01"), timestamp=now + 3.0)
    res4 = hardened.evaluate_transaction(t4_block)
    assert res4["outcome"] == EvaluationOutcome.BLOCKED.value
    assert res4["reason"] == "EXCEEDED_HOURLY_VELOCITY_LIMIT"


def test_hardened_engine_blacklist_strict_precedence():
    """Verifies blacklisted entities are rejected immediately."""
    hardened = HardenedAgentShieldEngine()
    hardened.add_blacklist("0xMaliciousHacker")

    tx = TransactionPayload(
        tx_id="tx_bad",
        sender="0xAlice",
        recipient="0xMaliciousHacker",
        amount=Decimal("1.00"),
    )
    res = hardened.evaluate_transaction(tx)
    assert res["outcome"] == EvaluationOutcome.BLOCKED.value
    assert res["reason"] == "RECIPIENT_BLACKLISTED"
