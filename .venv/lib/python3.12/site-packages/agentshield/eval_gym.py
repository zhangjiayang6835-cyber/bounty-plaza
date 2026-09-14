"""
AgentShield Eval Gym — 50 Scenarios
=====================================
50 labeled test cases spanning 7 categories, testing the SpendControlEngine
against real-world agent spending patterns.

Categories (50 total):
  - clean_approval (10):        Normal transactions that should pass
  - transaction_limit_block (8): Single transactions exceeding max amount
  - daily_total_block (7):       Cumulative daily spend exceeding cap
  - velocity_flag (6):           Rapid-fire transactions triggering velocity cap
  - merchant_allowlist_block (7): Transactions to unlisted merchants
  - category_block (7):          Transactions in blocked categories
  - edge_cases (5):              Boundary values, malformed inputs, empty rules
"""

import sys
import os
# Package import - no sys.path manipulation needed

from agentshield.engine import SpendControlEngine


def _txn(txn_id, amount=10.00, merchant="openai-api", category="llm_inference",
         agent_id="agent_a", timestamp="2026-08-10T10:00:00Z"):
    return {
        "id": txn_id, "agent_id": agent_id, "amount": amount,
        "merchant": merchant, "category": category,
        "timestamp": timestamp, "metadata": {}
    }


def _prior(agent_id, amount, timestamp):
    return {"agent_id": agent_id, "amount": amount, "timestamp": timestamp}


SCENARIOS = [

    # ═══ CLEAN APPROVAL (10) ═══
    {"id": 1, "category": "clean_approval",
     "transaction": _txn("t001", amount=10.00),
     "rules": [{"id": "r1", "type": "transaction_limit", "priority": 1, "params": {"max_amount": 500}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "APPROVED",
     "description": "Small transaction under all limits"},

    {"id": 2, "category": "clean_approval",
     "transaction": _txn("t002", amount=50.00, merchant="anthropic-api"),
     "rules": [{"id": "r1", "type": "transaction_limit", "priority": 1, "params": {"max_amount": 500}, "action": "BLOCK"},
               {"id": "r2", "type": "merchant_allowlist", "priority": 2, "params": {"allowed": ["openai-api", "anthropic-api"]}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "APPROVED",
     "description": "Normal Anthropic API call"},

    {"id": 3, "category": "clean_approval",
     "transaction": _txn("t003", amount=5.00, category="embedding"),
     "rules": [{"id": "r1", "type": "category_block", "priority": 1, "params": {"blocked": ["crypto_exchange"]}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "APPROVED",
     "description": "Embedding call in non-blocked category"},

    {"id": 4, "category": "clean_approval",
     "transaction": _txn("t004", amount=100.00),
     "rules": [{"id": "r1", "type": "daily_total", "priority": 1, "params": {"max_daily": 2000}, "action": "BLOCK"}],
     "prior_transactions": [_prior("agent_a", 200, "2026-08-10T09:00:00Z")],
     "expected": "APPROVED",
     "description": "Within daily total (300 < 2000)"},

    {"id": 5, "category": "clean_approval",
     "transaction": _txn("t005", amount=25.00, timestamp="2026-08-10T10:00:00Z"),
     "rules": [{"id": "r1", "type": "velocity", "priority": 1, "params": {"window_minutes": 60, "max_count": 10}, "action": "FLAGGED"}],
     "prior_transactions": [_prior("agent_a", 10, f"2026-08-10T09:5{i}:00Z") for i in range(3)],
     "expected": "APPROVED",
     "description": "4 total in window, under limit of 10"},

    {"id": 6, "category": "clean_approval",
     "transaction": _txn("t006", amount=0.01),
     "rules": [{"id": "r1", "type": "transaction_limit", "priority": 1, "params": {"max_amount": 500}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "APPROVED",
     "description": "Minimum viable transaction"},

    {"id": 7, "category": "clean_approval",
     "transaction": _txn("t007", amount=300.00),
     "rules": [{"id": "r1", "type": "transaction_limit", "priority": 1, "params": {"max_amount": 500}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "APPROVED",
     "description": "High but under single-transaction limit"},

    {"id": 8, "category": "clean_approval",
     "transaction": _txn("t008", amount=15.00, merchant="stripe-api"),
     "rules": [{"id": "r1", "type": "merchant_allowlist", "priority": 1, "params": {"allowed": ["openai-api", "anthropic-api", "stripe-api"]}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "APPROVED",
     "description": "Allowed merchant"},

    {"id": 9, "category": "clean_approval",
     "transaction": _txn("t009", amount=42.50, category="data_storage"),
     "rules": [{"id": "r1", "type": "category_block", "priority": 1, "params": {"blocked": ["crypto_exchange", "adult_content"]}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "APPROVED",
     "description": "Standard category not in blocklist"},

    {"id": 10, "category": "clean_approval",
     "transaction": _txn("t010", amount=250.00),
     "rules": [{"id": "r1", "type": "daily_total", "priority": 1, "params": {"max_daily": 2000}, "action": "BLOCK"}],
     "prior_transactions": [_prior("agent_a", 500, "2026-08-10T08:00:00Z"),
                            _prior("agent_a", 300, "2026-08-10T09:00:00Z")],
     "expected": "APPROVED",
     "description": "Daily total 1050 < 2000"},

    # ═══ TRANSACTION LIMIT BLOCK (8) ═══
    {"id": 11, "category": "transaction_limit_block",
     "transaction": _txn("t011", amount=750.00),
     "rules": [{"id": "r1", "type": "transaction_limit", "priority": 1, "params": {"max_amount": 500}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "BLOCKED",
     "description": "$750 exceeds $500 limit"},

    {"id": 12, "category": "transaction_limit_block",
     "transaction": _txn("t012", amount=500.01),
     "rules": [{"id": "r1", "type": "transaction_limit", "priority": 1, "params": {"max_amount": 500}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "BLOCKED",
     "description": "Limit + $0.01 triggers block"},

    {"id": 13, "category": "transaction_limit_block",
     "transaction": _txn("t013", amount=10000.00),
     "rules": [{"id": "r1", "type": "transaction_limit", "priority": 1, "params": {"max_amount": 500}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "BLOCKED",
     "description": "Extreme amount blocked"},

    {"id": 14, "category": "transaction_limit_block",
     "transaction": _txn("t014", amount=600.00),
     "rules": [{"id": "r1", "type": "transaction_limit", "priority": 1, "params": {"max_amount": 500}, "action": "BLOCK"},
               {"id": "r2", "type": "merchant_allowlist", "priority": 2, "params": {"allowed": ["openai-api"]}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "BLOCKED",
     "description": "Over limit — transaction_limit fires first (priority 1)"},

    {"id": 15, "category": "transaction_limit_block",
     "transaction": _txn("t015", amount=501.00),
     "rules": [{"id": "r1", "type": "transaction_limit", "priority": 1, "params": {"max_amount": 500}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "BLOCKED",
     "description": "$501 over $500 limit"},

    {"id": 16, "category": "transaction_limit_block",
     "transaction": _txn("t016", amount=1500.00, merchant="anthropic-api"),
     "rules": [{"id": "r1", "type": "merchant_allowlist", "priority": 1, "params": {"allowed": ["openai-api", "anthropic-api"]}, "action": "BLOCK"},
               {"id": "r2", "type": "transaction_limit", "priority": 2, "params": {"max_amount": 500}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "BLOCKED",
     "description": "Merchant passes allowlist but amount triggers limit at priority 2"},

    {"id": 17, "category": "transaction_limit_block",
     "transaction": _txn("t017", amount=999.99),
     "rules": [{"id": "r1", "type": "transaction_limit", "priority": 1, "params": {"max_amount": 999.98}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "BLOCKED",
     "description": "$999.99 over $999.98 limit"},

    {"id": 18, "category": "transaction_limit_block",
     "transaction": _txn("t018", amount=1000000.00),
     "rules": [{"id": "r1", "type": "transaction_limit", "priority": 1, "params": {"max_amount": 500}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "BLOCKED",
     "description": "Million-dollar runaway blocked"},

    # ═══ DAILY TOTAL BLOCK (7) ═══
    {"id": 19, "category": "daily_total_block",
     "transaction": _txn("t019", amount=100.00),
     "rules": [{"id": "r1", "type": "daily_total", "priority": 1, "params": {"max_daily": 2000}, "action": "BLOCK"}],
     "prior_transactions": [_prior("agent_a", 2000, "2026-08-10T01:00:00Z")],
     "expected": "BLOCKED",
     "description": "Daily total 2100 > 2000"},

    {"id": 20, "category": "daily_total_block",
     "transaction": _txn("t020", amount=1.00),
     "rules": [{"id": "r1", "type": "daily_total", "priority": 1, "params": {"max_daily": 100}, "action": "BLOCK"}],
     "prior_transactions": [_prior("agent_a", 100, "2026-08-10T01:00:00Z")],
     "expected": "BLOCKED",
     "description": "Already at cap, any amount overflows"},

    {"id": 21, "category": "daily_total_block",
     "transaction": _txn("t021", amount=500.00),
     "rules": [{"id": "r1", "type": "daily_total", "priority": 1, "params": {"max_daily": 2000}, "action": "BLOCK"}],
     "prior_transactions": [_prior("agent_a", 1000, "2026-08-10T06:00:00Z"),
                            _prior("agent_a", 600, "2026-08-10T07:00:00Z")],
     "expected": "BLOCKED",
     "description": "Daily total 2100 > 2000"},

    {"id": 22, "category": "daily_total_block",
     "transaction": _txn("t022", amount=100.00),
     "rules": [{"id": "r1", "type": "daily_total", "priority": 1, "params": {"max_daily": 100}, "action": "BLOCK"}],
     "prior_transactions": [_prior("agent_a", 1, "2026-08-10T01:00:00Z")],
     "expected": "BLOCKED",
     "description": "Daily total 101 > 100"},

    {"id": 23, "category": "daily_total_block",
     "transaction": _txn("t023", amount=250.00),
     "rules": [{"id": "r1", "type": "daily_total", "priority": 1, "params": {"max_daily": 500}, "action": "BLOCK"}],
     "prior_transactions": [_prior("agent_a", 300, "2026-08-10T01:00:00Z")],
     "expected": "BLOCKED",
     "description": "Daily total 550 > 500"},

    {"id": 24, "category": "daily_total_block",
     "transaction": _txn("t024", amount=500.00),
     "rules": [{"id": "r1", "type": "daily_total", "priority": 1, "params": {"max_daily": 500}, "action": "BLOCK"}],
     "prior_transactions": [_prior("agent_a", 1, "2026-08-10T01:00:00Z")],
     "expected": "BLOCKED",
     "description": "501 > 500 cap"},

    {"id": 25, "category": "daily_total_block",
     "transaction": _txn("t025", amount=200.00),
     "rules": [{"id": "r1", "type": "daily_total", "priority": 1, "params": {"max_daily": 2000}, "action": "BLOCK"}],
     "prior_transactions": [_prior("agent_a", 1850, "2026-08-10T01:00:00Z")],
     "expected": "BLOCKED",
     "description": "Daily total 2050 > 2000"},

    # ═══ VELOCITY FLAG (6) ═══
    {"id": 26, "category": "velocity_flag",
     "transaction": _txn("t026", amount=10.00, timestamp="2026-08-10T10:30:00Z"),
     "rules": [{"id": "r1", "type": "velocity", "priority": 1, "params": {"window_minutes": 60, "max_count": 5}, "action": "FLAGGED"}],
     "prior_transactions": [_prior("agent_a", 10, f"2026-08-10T10:2{i}:00Z") for i in range(5)],
     "expected": "FLAGGED",
     "description": "6 transactions in 60min window (limit 5)"},

    {"id": 27, "category": "velocity_flag",
     "transaction": _txn("t027", amount=5.00, timestamp="2026-08-10T10:30:00Z"),
     "rules": [{"id": "r1", "type": "velocity", "priority": 1, "params": {"window_minutes": 60, "max_count": 10}, "action": "FLAGGED"}],
     "prior_transactions": [_prior("agent_a", 5, f"2026-08-10T10:2{i}:00Z") for i in range(10)],
     "expected": "FLAGGED",
     "description": "11 transactions in window (limit 10)"},

    {"id": 28, "category": "velocity_flag",
     "transaction": _txn("t028", amount=1.00, timestamp="2026-08-10T10:30:00Z"),
     "rules": [{"id": "r1", "type": "velocity", "priority": 1, "params": {"window_minutes": 60, "max_count": 3}, "action": "FLAGGED"}],
     "prior_transactions": [_prior("agent_a", 1, "2026-08-10T10:29:00Z"),
                            _prior("agent_a", 1, "2026-08-10T10:28:00Z"),
                            _prior("agent_a", 1, "2026-08-10T10:27:00Z")],
     "expected": "FLAGGED",
     "description": "4 transactions in 60min window (limit 3)"},

    {"id": 29, "category": "velocity_flag",
     "transaction": _txn("t029", amount=2.00, timestamp="2026-08-10T10:30:00Z"),
     "rules": [{"id": "r1", "type": "velocity", "priority": 1, "params": {"window_minutes": 60, "max_count": 2}, "action": "FLAGGED"}],
     "prior_transactions": [_prior("agent_a", 2, "2026-08-10T10:00:00Z"),
                            _prior("agent_a", 2, "2026-08-10T10:15:00Z")],
     "expected": "FLAGGED",
     "description": "3 transactions in 60min window (limit 2)"},

    {"id": 30, "category": "velocity_flag",
     "transaction": _txn("t030", amount=5.00, timestamp="2026-08-10T12:00:00Z"),
     "rules": [{"id": "r1", "type": "velocity", "priority": 1, "params": {"window_minutes": 60, "max_count": 5}, "action": "FLAGGED"}],
     "prior_transactions": [_prior("agent_a", 5, f"2026-08-10T11:5{i}:00Z") for i in range(5)],
     "expected": "FLAGGED",
     "description": "6 transactions in 60min window (limit 5)"},

    {"id": 31, "category": "velocity_flag",
     "transaction": _txn("t031", amount=3.00, timestamp="2026-08-10T12:00:00Z"),
     "rules": [{"id": "r1", "type": "velocity", "priority": 1, "params": {"window_minutes": 30, "max_count": 3}, "action": "FLAGGED"}],
     "prior_transactions": [_prior("agent_a", 3, "2026-08-10T11:40:00Z"),
                            _prior("agent_a", 3, "2026-08-10T11:45:00Z"),
                            _prior("agent_a", 3, "2026-08-10T11:50:00Z")],
     "expected": "FLAGGED",
     "description": "4 transactions in 30min window (limit 3)"},

    # ═══ MERCHANT ALLOWLIST BLOCK (7) ═══
    {"id": 32, "category": "merchant_allowlist_block",
     "transaction": _txn("t032", amount=10.00, merchant="unknown-api"),
     "rules": [{"id": "r1", "type": "merchant_allowlist", "priority": 1, "params": {"allowed": ["openai-api", "anthropic-api"]}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "BLOCKED",
     "description": "Unknown merchant blocked"},

    {"id": 33, "category": "merchant_allowlist_block",
     "transaction": _txn("t033", amount=50.00, merchant="unauthorized-vendor"),
     "rules": [{"id": "r1", "type": "merchant_allowlist", "priority": 1, "params": {"allowed": ["openai-api"]}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "BLOCKED",
     "description": "Unauthorized vendor blocked"},

    {"id": 34, "category": "merchant_allowlist_block",
     "transaction": _txn("t034", amount=100.00, merchant="suspicious-api"),
     "rules": [{"id": "r1", "type": "merchant_allowlist", "priority": 1, "params": {"allowed": ["openai-api", "anthropic-api", "stripe-api"]}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "BLOCKED",
     "description": "Suspicious merchant blocked"},

    {"id": 35, "category": "merchant_allowlist_block",
     "transaction": _txn("t035", amount=25.00, merchant="random-llm-proxy"),
     "rules": [{"id": "r1", "type": "merchant_allowlist", "priority": 1, "params": {"allowed": ["openai-api", "anthropic-api"]}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "BLOCKED",
     "description": "Random LLM proxy blocked"},

    {"id": 36, "category": "merchant_allowlist_block",
     "transaction": _txn("t036", amount=15.00, merchant="dark-market"),
     "rules": [{"id": "r1", "type": "merchant_allowlist", "priority": 1, "params": {"allowed": ["openai-api"]}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "BLOCKED",
     "description": "Dark market merchant blocked"},

    {"id": 37, "category": "merchant_allowlist_block",
     "transaction": _txn("t037", amount=500.00, merchant="unknown-api"),
     "rules": [{"id": "r1", "type": "transaction_limit", "priority": 1, "params": {"max_amount": 1000}, "action": "BLOCK"},
               {"id": "r2", "type": "merchant_allowlist", "priority": 2, "params": {"allowed": ["openai-api"]}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "BLOCKED",
     "description": "Under tx limit, but merchant not allowed"},

    {"id": 38, "category": "merchant_allowlist_block",
     "transaction": _txn("t038", amount=20.00, merchant="new-vendor"),
     "rules": [{"id": "r1", "type": "merchant_allowlist", "priority": 1, "params": {"allowed": ["openai-api"]}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "BLOCKED",
     "description": "New merchant not in allowlist"},

    # ═══ CATEGORY BLOCK (7) ═══
    {"id": 39, "category": "category_block",
     "transaction": _txn("t039", amount=100.00, category="crypto_exchange"),
     "rules": [{"id": "r1", "type": "category_block", "priority": 1, "params": {"blocked": ["crypto_exchange", "adult_content"]}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "BLOCKED",
     "description": "Crypto exchange blocked"},

    {"id": 40, "category": "category_block",
     "transaction": _txn("t040", amount=50.00, category="adult_content"),
     "rules": [{"id": "r1", "type": "category_block", "priority": 1, "params": {"blocked": ["crypto_exchange", "adult_content"]}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "BLOCKED",
     "description": "Adult content blocked"},

    {"id": 41, "category": "category_block",
     "transaction": _txn("t041", amount=200.00, category="gambling"),
     "rules": [{"id": "r1", "type": "category_block", "priority": 1, "params": {"blocked": ["gambling"]}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "BLOCKED",
     "description": "Gambling category blocked"},

    {"id": 42, "category": "category_block",
     "transaction": _txn("t042", amount=75.00, category="luxury_purchase"),
     "rules": [{"id": "r1", "type": "category_block", "priority": 1, "params": {"blocked": ["luxury_purchase"]}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "BLOCKED",
     "description": "Luxury purchase blocked"},

    {"id": 43, "category": "category_block",
     "transaction": _txn("t043", amount=10.00, category="unauthorized_purchase"),
     "rules": [{"id": "r1", "type": "category_block", "priority": 1, "params": {"blocked": ["unauthorized_purchase"]}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "BLOCKED",
     "description": "Unauthorized purchase blocked"},

    {"id": 44, "category": "category_block",
     "transaction": _txn("t044", amount=300.00, category="crypto_exchange"),
     "rules": [{"id": "r1", "type": "transaction_limit", "priority": 1, "params": {"max_amount": 500}, "action": "BLOCK"},
               {"id": "r2", "type": "category_block", "priority": 2, "params": {"blocked": ["crypto_exchange"]}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "BLOCKED",
     "description": "Under tx limit, crypto category blocked at priority 2"},

    {"id": 45, "category": "category_block",
     "transaction": _txn("t045", amount=10.00, category="unauthorized_service"),
     "rules": [{"id": "r1", "type": "category_block", "priority": 1, "params": {"blocked": ["unauthorized_service"]}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "BLOCKED",
     "description": "Unauthorized service blocked"},

    # ═══ EDGE CASES (5) ═══
    {"id": 46, "category": "edge_cases",
     "transaction": _txn("t046", amount=500.00),
     "rules": [{"id": "r1", "type": "transaction_limit", "priority": 1, "params": {"max_amount": 500}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "APPROVED",
     "description": "Amount EXACTLY at limit should APPROVE (not strictly greater)"},

    {"id": 47, "category": "edge_cases",
     "transaction": {"id": "t047", "agent_id": "agent_a", "merchant": "openai-api",
                     "category": "llm_inference", "timestamp": "2026-08-10T10:00:00Z"},
     "rules": [{"id": "r1", "type": "transaction_limit", "priority": 1, "params": {"max_amount": 500}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "FLAGGED",
     "description": "Missing amount field yields FLAGGED"},

    {"id": 48, "category": "edge_cases",
     "transaction": _txn("t048", amount=10.00),
     "rules": [],
     "prior_transactions": [], "expected": "APPROVED",
     "description": "Empty rules list yields APPROVED"},

    {"id": 49, "category": "edge_cases",
     "transaction": _txn("t049", amount=10.00),
     "rules": [{"id": "r1", "type": "transaction_limit", "priority": 5, "params": {"max_amount": 100}, "action": "BLOCK"},
               {"id": "r2", "type": "transaction_limit", "priority": 5, "params": {"max_amount": 5000}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "APPROVED",
     "description": "Two rules at same priority, neither triggers"},

    {"id": 50, "category": "edge_cases",
     "transaction": _txn("t050", amount=10.00),
     "rules": [{"id": "r1", "type": "transaction_limit", "priority": 1, "params": {"max_amount": 5}, "action": "BLOCK"},
               {"id": "r2", "type": "transaction_limit", "priority": 1, "params": {"max_amount": 5000}, "action": "BLOCK"}],
     "prior_transactions": [], "expected": "BLOCKED",
     "description": "Same priority — first rule (max_amount=5) blocks $10"},

    # ─── Session Budget (inspired by HeartFlow / @yun520-1) ───
    {"id": 51, "category": "session_budget",
     "transaction": {**_txn("t051", amount=150.00), "session_id": "sess_1"},
     "rules": [{"id": "sb1", "type": "session_budget", "priority": 1,
                "params": {"max_session": 500}, "action": "BLOCK"}],
     "prior_transactions": [
         {**_txn("t050a", amount=400.00), "session_id": "sess_1"},
     ],
     "expected": "BLOCKED",
     "description": "Session total $550 exceeds $500 session budget"},

    {"id": 52, "category": "session_budget",
     "transaction": {**_txn("t052", amount=100.00), "session_id": "sess_2"},
     "rules": [{"id": "sb2", "type": "session_budget", "priority": 1,
                "params": {"max_session": 500}, "action": "BLOCK"}],
     "prior_transactions": [
         {**_txn("t052a", amount=200.00), "session_id": "sess_2"},
     ],
     "expected": "APPROVED",
     "description": "Session total $300 under $500 session budget — approved"},

    {"id": 53, "category": "session_budget",
     "transaction": {**_txn("t053", amount=50.00), "session_id": "sess_3"},
     "rules": [{"id": "sb3", "type": "session_budget", "priority": 1,
                "params": {"max_session": 500}, "action": "BLOCK"}],
     "prior_transactions": [
         {**_txn("t053a", amount=200.00), "session_id": "sess_4"},  # Different session
     ],
     "expected": "APPROVED",
     "description": "Prior transaction in different session — not counted"},

    # ─── Cascade Cost (inspired by HeartFlow / @yun520-1) ───
    {"id": 54, "category": "cascade_cost",
     "transaction": {**_txn("t054", amount=50.00), "fail_probability": 0.3, "reversal_cost": 200},
     "rules": [{"id": "cc1", "type": "cascade_cost", "priority": 1,
                "params": {"max_cascade_cost": 100}, "action": "BLOCK"}],
     "prior_transactions": [],
     "expected": "BLOCKED",
     "description": "Cascade cost $110 ($50 + 30% × $200) exceeds $100 limit"},

    {"id": 55, "category": "cascade_cost",
     "transaction": {**_txn("t055", amount=10.00), "fail_probability": 0.1, "reversal_cost": 50},
     "rules": [{"id": "cc2", "type": "cascade_cost", "priority": 1,
                "params": {"max_cascade_cost": 100}, "action": "BLOCK"}],
     "prior_transactions": [],
     "expected": "APPROVED",
     "description": "Cascade cost $15 ($10 + 10% × $50) under $100 limit"},

    {"id": 56, "category": "cascade_cost",
     "transaction": {**_txn("t056", amount=10.00), "estimated_cascade_cost": 150},
     "rules": [{"id": "cc3", "type": "cascade_cost", "priority": 1,
                "params": {"max_cascade_cost": 100}, "action": "BLOCK"}],
     "prior_transactions": [],
     "expected": "BLOCKED",
     "description": "Pre-computed cascade cost $150 exceeds $100 limit"},
]


def run_eval() -> dict:
    """Run all 50 scenarios and return results dict."""
    engine = SpendControlEngine()
    results = {"total": 0, "passed": 0, "failed": 0, "by_category": {}, "failures": []}

    for scenario in SCENARIOS:
        result = engine.evaluate(
            scenario["transaction"],
            scenario["rules"],
            scenario["prior_transactions"]
        )
        cat = scenario["category"]
        results["by_category"].setdefault(cat, {"total": 0, "passed": 0})
        results["by_category"][cat]["total"] += 1
        results["total"] += 1

        if result["decision"] == scenario["expected"]:
            results["passed"] += 1
            results["by_category"][cat]["passed"] += 1
        else:
            results["failed"] += 1
            results["failures"].append({
                "scenario": scenario["id"],
                "expected": scenario["expected"],
                "got": result["decision"],
                "reason": result.get("reason"),
                "description": scenario["description"]
            })

    return results


def generate_report(results: dict) -> str:
    """Generate a markdown report from eval results."""
    total = results['total']
    passed = results['passed']
    pct = passed / total * 100 if total else 0

    md = f"# AgentShield Eval Gym Report\n\n"
    md += f"**Overall:** {passed}/{total} ({pct:.1f}%)\n\n"
    md += "## By Category\n\n"
    md += "| Category | Passed | Total | Rate |\n"
    md += "|----------|--------|-------|------|\n"
    for cat, data in sorted(results["by_category"].items()):
        rate = data['passed'] / data['total'] * 100 if data['total'] else 0
        md += f"| {cat} | {data['passed']} | {data['total']} | {rate:.0f}% |\n"

    if results['failures']:
        md += "\n## Failures\n\n"
        for f in results['failures']:
            md += f"- **Scenario {f['scenario']}**: Expected `{f['expected']}`, got `{f['got']}` — {f['description']}\n"

    return md


if __name__ == '__main__':
    results = run_eval()
    print(f"{results['passed']}/{results['total']} passed")
    if results['failed']:
        print("FAILURES:")
        for f in results['failures']:
            print(f"  Scenario {f['scenario']}: expected {f['expected']} got {f['got']}")
    else:
        print("ALL PASSED")
    report = generate_report(results)
    report_path = os.path.join('/tmp', 'agentshield-eval-report.md')
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"Report: {report_path}")
