# AgentShield bounty submission (issue #819 / upstream #1)

**Primary submission:** `session_budget` decay false positive (session budget miscalculation).

**Package:** `agentshield-spend==1.0.1` (`pip install agentshield-spend`)

**Category:** False positive — legitimate transaction wrongly blocked.

## Reproduction

```python
from agentshield import SpendControlEngine

engine = SpendControlEngine()

rules = [{
    "id": "sb_decay",
    "type": "session_budget",
    "priority": 1,
    "params": {"max_session": 100, "decay_factor": 0.3},
    "action": "BLOCK",
}]

priors = [{
    "amount": 90,
    "agent_id": "agent_a",
    "session_id": "sess_decay",
    "merchant": "openai-api",
    "category": "llm_inference",
}]

txn = {
    "amount": 5,
    "merchant": "openai-api",
    "category": "llm_inference",
    "agent_id": "agent_a",
    "session_id": "sess_decay",
    "timestamp": "2026-08-10T12:00:00Z",
}

print(engine.evaluate(txn, rules, priors))
# Got: BLOCKED — Session decay: per-call cap $1.50 (remaining $5.00 < 30% of session budget)
# Expected: APPROVED — session total $95 is under $100 max_session
```

Decay tightening fires after the main budget check passes (`session_total <= max_session`), shrinking the per-call cap below the current amount even though cumulative spend remains within budget.

## Secondary candidates (not submitting first)

| ID | Type | Rule |
|----|------|------|
| `bounty_tz_daily` | False negative | `daily_total` timezone date slice |
| `bounty_dt_ts` | False negative | `daily_total` missing timestamp |
| `bounty_neg_prior` | False negative | `daily_total` negative prior |
| `bounty_cascade_neg` | False negative | `cascade_cost` negative pre-computed |
| `bounty_vel_ts` | False negative | `velocity` missing timestamp |

Run all scenarios: `make eval-gym` or `python -m pytest -q`.
