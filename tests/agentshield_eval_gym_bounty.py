"""
Eval-gym-style bounty scenarios for AgentShield SpendControlEngine (6 scenarios).

Run: python -m tests.agentshield_eval_gym_bounty
"""

from agentshield import SpendControlEngine

engine = SpendControlEngine()

SCENARIOS = [
    {
        "id": "bounty_tz_daily",
        "category": "daily_total_false_negative",
        "description": "Same instant, different date strings bypass daily_total",
        "transaction": {
            "amount": 20,
            "merchant": "openai-api",
            "category": "llm_inference",
            "agent_id": "agent_a",
            "timestamp": "2026-08-11T04:00:00Z",
        },
        "rules": [
            {
                "id": "dt_tz",
                "type": "daily_total",
                "priority": 1,
                "params": {"max_daily": 50},
                "action": "BLOCK",
            }
        ],
        "prior_transactions": [
            {
                "agent_id": "agent_a",
                "amount": 40,
                "timestamp": "2026-08-10T23:00:00-05:00",
            }
        ],
        "expected": "BLOCKED",
    },
    {
        "id": "bounty_decay_fp",
        "category": "session_budget_false_positive",
        "description": "Decay blocks txn under max_session (95 < 100)",
        "transaction": {
            "amount": 5,
            "merchant": "openai-api",
            "category": "llm_inference",
            "agent_id": "agent_a",
            "session_id": "sess_decay",
            "timestamp": "2026-08-10T12:00:00Z",
        },
        "rules": [
            {
                "id": "sb_decay",
                "type": "session_budget",
                "priority": 1,
                "params": {"max_session": 100, "decay_factor": 0.3},
                "action": "BLOCK",
            }
        ],
        "prior_transactions": [
            {
                "amount": 90,
                "agent_id": "agent_a",
                "session_id": "sess_decay",
                "merchant": "openai-api",
                "category": "llm_inference",
            }
        ],
        "expected": "APPROVED",
    },
    {
        "id": "bounty_neg_prior",
        "category": "daily_total_false_negative",
        "description": "Negative prior reduces counted daily spend",
        "transaction": {
            "amount": 45,
            "merchant": "openai-api",
            "category": "llm_inference",
            "agent_id": "agent_a",
            "timestamp": "2026-08-10T03:00:00Z",
        },
        "rules": [
            {
                "id": "dt_neg",
                "type": "daily_total",
                "priority": 1,
                "params": {"max_daily": 50},
                "action": "BLOCK",
            }
        ],
        "prior_transactions": [
            {"agent_id": "agent_a", "amount": -1000, "timestamp": "2026-08-10T01:00:00Z"},
            {"agent_id": "agent_a", "amount": 45, "timestamp": "2026-08-10T02:00:00Z"},
        ],
        "expected": "BLOCKED",
    },
    {
        "id": "bounty_cascade_neg",
        "category": "cascade_cost_false_negative",
        "description": "Negative estimated_cascade_cost bypasses cascade_cost rule",
        "transaction": {
            "amount": 9999,
            "merchant": "openai-api",
            "category": "llm_inference",
            "estimated_cascade_cost": -1,
        },
        "rules": [
            {
                "id": "cc_neg",
                "type": "cascade_cost",
                "priority": 1,
                "params": {"max_cascade_cost": 10},
                "action": "BLOCK",
            }
        ],
        "prior_transactions": [],
        "expected": "BLOCKED",
    },
    {
        "id": "bounty_dt_ts",
        "category": "daily_total_false_negative",
        "description": "Missing timestamp on txn skips prior daily spend",
        "transaction": {
            "amount": 20,
            "merchant": "openai-api",
            "category": "llm_inference",
            "agent_id": "agent_a",
        },
        "rules": [
            {
                "id": "dt_ts",
                "type": "daily_total",
                "priority": 1,
                "params": {"max_daily": 50},
                "action": "BLOCK",
            }
        ],
        "prior_transactions": [
            {
                "agent_id": "agent_a",
                "amount": 40,
                "timestamp": "2026-08-10T11:00:00Z",
            }
        ],
        "expected": "BLOCKED",
    },
    {
        "id": "bounty_vel_ts",
        "category": "velocity_false_negative",
        "description": "Missing timestamp skips velocity rule entirely",
        "transaction": {
            "amount": 1,
            "merchant": "openai-api",
            "category": "llm_inference",
            "agent_id": "agent_a",
        },
        "rules": [
            {
                "id": "vel_ts",
                "type": "velocity",
                "priority": 1,
                "params": {"window_minutes": 60, "max_count": 2},
                "action": "BLOCK",
            }
        ],
        "prior_transactions": [
            {"agent_id": "agent_a", "amount": 1, "timestamp": "2026-08-10T10:00:00Z"},
            {"agent_id": "agent_a", "amount": 1, "timestamp": "2026-08-10T10:05:00Z"},
            {"agent_id": "agent_a", "amount": 1, "timestamp": "2026-08-10T10:10:00Z"},
        ],
        "expected": "BLOCKED",
    },
]


def run_eval() -> dict:
    results = {"total": 0, "passed": 0, "failed": 0, "failures": []}
    for scenario in SCENARIOS:
        result = engine.evaluate(
            scenario["transaction"],
            scenario["rules"],
            scenario["prior_transactions"],
        )
        results["total"] += 1
        if result["decision"] == scenario["expected"]:
            results["passed"] += 1
        else:
            results["failed"] += 1
            results["failures"].append(
                {
                    "id": scenario["id"],
                    "expected": scenario["expected"],
                    "got": result["decision"],
                    "reason": result.get("reason"),
                    "description": scenario["description"],
                }
            )
    return results


if __name__ == "__main__":
    results = run_eval()
    print(f"{results['passed']}/{results['total']} engine matches expected (correct) behavior")
    if results["failures"]:
        print("CONFIRMED BUGS (engine deviates from expected):")
        for failure in results["failures"]:
            print(
                f"  - {failure['id']}: expected {failure['expected']}, "
                f"got {failure['got']} — {failure['description']}"
            )
            if failure.get("reason"):
                print(f"    reason: {failure['reason']}")
