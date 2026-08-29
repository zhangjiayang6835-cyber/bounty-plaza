#!/usr/bin/env python3
"""
AgentShield Rules Engine Vulnerability Reproduction & Verification Suite
========================================================================
Target: kindrat86/agentshield (Issue #1 / Bounty Plaza #819)
Author: Universal Engineer

Identified Vulnerabilities:
  1. Session Decay Tightening Inversion / Zero-Cap Bypass (False Negative)
     - Root Cause: In `_check_session_budget`, when `session_total == max_session`
       (`remaining == 0`), `per_call_cap = Decimal('0')`. The condition
       `if txn_amount > per_call_cap and per_call_cap > Decimal('0'):` evaluates to False
       because `Decimal('0') > Decimal('0')` is False. Consequently, a transaction that
       exhausts 100% of remaining budget bypasses decay tightening, while a smaller
       transaction is blocked.
  2. Merchant Allowlist Bypass via Empty String / Falsy Merchant (False Negative)
     - Root Cause: In `_check_merchant_allowlist`, `if merchant and merchant not in allowed:`
       evaluates to False when `merchant == ""` (or `None`), allowing unauthorized
       empty-string merchant requests to bypass strict whitelist policies.
  3. Negative Amount Bypass on Non-Transaction-Limit Rules (False Negative)
     - Root Cause: `evaluate()` does not validate `amount > 0`. Only `_check_transaction_limit`
       contains a non-positive check. When rules only specify `daily_total` or `session_budget`,
       negative transaction amounts pass validation and subtract from spend totals.
  4. Timezone Offset Evasion in Daily Spend Aggregation (False Negative)
     - Root Cause: `_extract_date(ts_str)` uses crude string slicing `ts_str[:10]`.
       Transactions sent with local timezone offsets (e.g. `2026-08-10T23:30:00-05:00` vs
       `2026-08-11T04:30:00Z`) that occur on the exact same UTC date are treated as different
       days, bypassing daily spending caps.
"""

from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta, timezone
import json
import sys


def parse_ts(ts_str: str | None) -> datetime | None:
    """Parse an ISO timestamp string into a UTC datetime object."""
    if not ts_str:
        return None
    try:
        ts = ts_str
        if ts.endswith('Z'):
            ts = ts[:-1] + '+00:00'
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def extract_date_utc(ts_str: str | None) -> str | None:
    """Extract normalized UTC calendar date (YYYY-MM-DD) from timestamp."""
    dt = parse_ts(ts_str)
    if dt is None:
        return None
    return dt.strftime('%Y-%m-%d')


class VulnerableSpendControlEngine:
    """Original implementation from kindrat86/agentshield."""

    def evaluate(self, transaction: dict, rules: list, prior_transactions: list) -> dict:
        required_fields = ['amount', 'merchant', 'category']
        if not transaction or not all(k in transaction for k in required_fields):
            return {
                "decision": "BLOCKED",
                "reason": "Invalid transaction format: missing required fields (fail-closed)",
                "rule_triggered": None,
                "severity": "high"
            }

        try:
            txn_amount = Decimal(str(transaction['amount']))
        except (InvalidOperation, TypeError, ValueError):
            return {
                "decision": "BLOCKED",
                "reason": "Invalid transaction format: amount is not a valid number (fail-closed)",
                "rule_triggered": None,
                "severity": "high"
            }

        sorted_rules = sorted(
            enumerate(rules),
            key=lambda pair: (pair[1].get('priority', 999), pair[0])
        )

        for _original_index, rule in sorted_rules:
            result = self._evaluate_rule(rule, transaction, txn_amount, prior_transactions)
            if result is not None:
                return result

        return {
            "decision": "APPROVED",
            "reason": "All rules passed",
            "rule_triggered": None,
            "severity": "none"
        }

    def _evaluate_rule(self, rule: dict, transaction: dict, txn_amount: Decimal,
                       prior_transactions: list) -> dict | None:
        rule_type = rule.get('type')
        params = rule.get('params', {})
        action = rule.get('action', 'BLOCK')
        rule_id = rule.get('id', 'unknown')

        if rule_type == 'transaction_limit':
            max_amount = Decimal(str(params.get('max_amount', '0')))
            if txn_amount <= 0:
                return {"decision": "BLOCKED", "rule_triggered": rule_id, "reason": "Non-positive amount"}
            if txn_amount > max_amount:
                return {"decision": "BLOCKED", "rule_triggered": rule_id, "reason": "Exceeds max_amount"}
        elif rule_type == 'daily_total':
            max_daily = Decimal(str(params.get('max_daily', '0')))
            txn_date = transaction.get('timestamp', '')[:10] if transaction.get('timestamp') else None
            agent_id = transaction.get('agent_id')
            daily_total = txn_amount
            for prior in prior_transactions:
                if prior.get('agent_id') != agent_id:
                    continue
                prior_date = prior.get('timestamp', '')[:10] if prior.get('timestamp') else None
                if txn_date and prior_date and prior_date == txn_date:
                    prior_amount = Decimal(str(prior.get('amount', '0')))
                    if prior_amount > 0:
                        daily_total += prior_amount
            if daily_total > max_daily:
                return {"decision": "BLOCKED", "rule_triggered": rule_id, "reason": "Exceeds max_daily"}
        elif rule_type == 'merchant_allowlist':
            allowed = params.get('allowed', [])
            merchant = transaction.get('merchant')
            if merchant and merchant not in allowed:
                return {"decision": "BLOCKED", "rule_triggered": rule_id, "reason": "Merchant not allowed"}
        elif rule_type == 'session_budget':
            max_session = Decimal(str(params.get('max_session', '0')))
            session_field = params.get('session_id', 'session_id')
            session_id = transaction.get(session_field)
            agent_id = transaction.get('agent_id')
            decay_factor = params.get('decay_factor')

            session_total = txn_amount
            for prior in prior_transactions:
                if prior.get('agent_id') != agent_id:
                    continue
                if prior.get(session_field) == session_id:
                    prior_amount = Decimal(str(prior.get('amount', '0')))
                    if prior_amount > 0:
                        session_total += prior_amount

            if session_total > max_session:
                return {"decision": "BLOCKED", "rule_triggered": rule_id, "reason": "Exceeds max_session"}

            if decay_factor is not None:
                decay = float(decay_factor)
                if 0 < decay < 1:
                    remaining = max_session - session_total
                    if remaining < max_session * Decimal(str(decay)):
                        per_call_cap = remaining * Decimal(str(decay))
                        if txn_amount > per_call_cap and per_call_cap > Decimal('0'):
                            return {"decision": "BLOCKED", "rule_triggered": rule_id, "reason": "Session decay cap"}

        return None


class PatchedSpendControlEngine:
    """Hardened, secure implementation resolving all identified breaks."""

    def evaluate(self, transaction: dict, rules: list, prior_transactions: list) -> dict:
        required_fields = ['amount', 'merchant', 'category']
        if not transaction or not all(k in transaction for k in required_fields):
            return {
                "decision": "BLOCKED",
                "reason": "Invalid transaction format: missing required fields (fail-closed)",
                "rule_triggered": None,
                "severity": "high"
            }

        try:
            txn_amount = Decimal(str(transaction['amount']))
        except (InvalidOperation, TypeError, ValueError):
            return {
                "decision": "BLOCKED",
                "reason": "Invalid transaction format: amount is not a valid number (fail-closed)",
                "rule_triggered": None,
                "severity": "high"
            }

        # Global fail-closed non-positive validation
        if txn_amount <= 0:
            return {
                "decision": "BLOCKED",
                "reason": f"Transaction amount ${txn_amount} is not a positive value (fail-closed)",
                "rule_triggered": None,
                "severity": "high"
            }

        sorted_rules = sorted(
            enumerate(rules),
            key=lambda pair: (pair[1].get('priority', 999), pair[0])
        )

        for _original_index, rule in sorted_rules:
            result = self._evaluate_rule(rule, transaction, txn_amount, prior_transactions)
            if result is not None:
                return result

        return {
            "decision": "APPROVED",
            "reason": "All rules passed",
            "rule_triggered": None,
            "severity": "none"
        }

    def _evaluate_rule(self, rule: dict, transaction: dict, txn_amount: Decimal,
                       prior_transactions: list) -> dict | None:
        rule_type = rule.get('type')
        params = rule.get('params', {})
        rule_id = rule.get('id', 'unknown')

        if rule_type == 'transaction_limit':
            max_amount = Decimal(str(params.get('max_amount', '0')))
            if txn_amount > max_amount:
                return {"decision": "BLOCKED", "rule_triggered": rule_id, "reason": "Exceeds max_amount"}

        elif rule_type == 'daily_total':
            max_daily = Decimal(str(params.get('max_daily', '0')))
            txn_date = extract_date_utc(transaction.get('timestamp'))
            agent_id = transaction.get('agent_id')
            daily_total = txn_amount
            for prior in prior_transactions:
                if prior.get('agent_id') != agent_id:
                    continue
                prior_date = extract_date_utc(prior.get('timestamp'))
                if txn_date and prior_date and prior_date == txn_date:
                    prior_amount = Decimal(str(prior.get('amount', '0')))
                    if prior_amount > 0:
                        daily_total += prior_amount
            if daily_total > max_daily:
                return {"decision": "BLOCKED", "rule_triggered": rule_id, "reason": "Exceeds max_daily"}

        elif rule_type == 'merchant_allowlist':
            allowed = params.get('allowed', [])
            merchant = transaction.get('merchant')
            if merchant not in allowed:
                return {"decision": "BLOCKED", "rule_triggered": rule_id, "reason": f"Merchant '{merchant}' not in allowlist"}

        elif rule_type == 'session_budget':
            max_session = Decimal(str(params.get('max_session', '0')))
            session_field = params.get('session_id', 'session_id')
            session_id = transaction.get(session_field)
            agent_id = transaction.get('agent_id')
            decay_factor = params.get('decay_factor')

            session_total = txn_amount
            for prior in prior_transactions:
                if prior.get('agent_id') != agent_id:
                    continue
                if prior.get(session_field) == session_id:
                    prior_amount = Decimal(str(prior.get('amount', '0')))
                    if prior_amount > 0:
                        session_total += prior_amount

            if session_total > max_session:
                return {"decision": "BLOCKED", "rule_triggered": rule_id, "reason": "Exceeds max_session"}

            if decay_factor is not None:
                decay = float(decay_factor)
                if 0 < decay < 1:
                    remaining = max_session - session_total
                    if remaining < max_session * Decimal(str(decay)):
                        per_call_cap = remaining * Decimal(str(decay))
                        # Fix: If per_call_cap is <= 0 or txn_amount > per_call_cap when threshold exceeded
                        if txn_amount > per_call_cap:
                            return {"decision": "BLOCKED", "rule_triggered": rule_id, "reason": f"Session decay cap ${per_call_cap}"}

        return None


def run_reproduction_suite():
    print("=" * 70)
    print("AgentShield Rules Engine Vulnerability & Break Reproduction Suite")
    print("=" * 70)

    vuln_engine = VulnerableSpendControlEngine()
    patch_engine = PatchedSpendControlEngine()

    test_cases = [
        {
            "name": "Break 1: Session Decay Tightening Inversion (Zero-Cap Bypass)",
            "transaction": {"id": "t1", "amount": 10.0, "merchant": "openai", "category": "llm", "session_id": "s1"},
            "rules": [{"id": "sb1", "type": "session_budget", "priority": 1, "params": {"max_session": 100, "decay_factor": 0.5}, "action": "BLOCK"}],
            "priors": [{"agent_id": None, "amount": 90.0, "session_id": "s1", "timestamp": "2026-08-10T10:00:00Z"}],
            "expected_secure": "BLOCKED",
            "vulnerable_produces": "APPROVED",
        },
        {
            "name": "Break 2: Empty String Merchant Allowlist Bypass",
            "transaction": {"id": "t2", "amount": 50.0, "merchant": "", "category": "llm"},
            "rules": [{"id": "al1", "type": "merchant_allowlist", "priority": 1, "params": {"allowed": ["openai-api", "anthropic-api"]}, "action": "BLOCK"}],
            "priors": [],
            "expected_secure": "BLOCKED",
            "vulnerable_produces": "APPROVED",
        },
        {
            "name": "Break 3: Negative Amount Bypass on Daily Total Rule",
            "transaction": {"id": "t3", "amount": -100.0, "merchant": "openai", "category": "llm", "timestamp": "2026-08-10T10:00:00Z"},
            "rules": [{"id": "dt1", "type": "daily_total", "priority": 1, "params": {"max_daily": 100}, "action": "BLOCK"}],
            "priors": [],
            "expected_secure": "BLOCKED",
            "vulnerable_produces": "APPROVED",
        },
        {
            "name": "Break 4: Timezone Offset Evasion in Daily Total Aggregation",
            "transaction": {"id": "t4", "amount": 80.0, "merchant": "openai", "category": "llm", "timestamp": "2026-08-11T03:30:00Z"},
            "rules": [{"id": "dt2", "type": "daily_total", "priority": 1, "params": {"max_daily": 100}, "action": "BLOCK"}],
            "priors": [{"agent_id": None, "amount": 80.0, "timestamp": "2026-08-10T23:00:00-04:00"}],
            "expected_secure": "BLOCKED",
            "vulnerable_produces": "APPROVED",
        },
    ]

    for tc in test_cases:
        print(f"\n[Scenario] {tc['name']}")
        v_res = vuln_engine.evaluate(tc['transaction'], tc['rules'], tc['priors'])
        p_res = patch_engine.evaluate(tc['transaction'], tc['rules'], tc['priors'])

        print(f"  Vulnerable Engine Output: {v_res['decision']} (Expected Break: {tc['vulnerable_produces']})")
        print(f"  Patched Engine Output:    {p_res['decision']} (Secure Expected: {tc['expected_secure']})")
        assert v_res['decision'] == tc['vulnerable_produces'], f"Vulnerable engine did not produce {tc['vulnerable_produces']}"
        assert p_res['decision'] == tc['expected_secure'], f"Patched engine did not produce {tc['expected_secure']}"

    print("\n" + "=" * 70)
    print("All vulnerability reproductions verified successfully!")
    print("=" * 70)


if __name__ == "__main__":
    run_reproduction_suite()
