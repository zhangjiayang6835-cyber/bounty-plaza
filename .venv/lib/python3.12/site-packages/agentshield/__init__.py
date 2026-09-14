"""
AgentShield — A firewall for AI agent spending.

9 composable rules evaluated per-transaction in <1ms.
Pure Python 3.11 stdlib — zero dependencies.

Quick Start:
    from agentshield import SpendControlEngine, run_eval

    engine = SpendControlEngine()
    result = engine.evaluate(transaction, rules, prior_transactions)
    print(result["decision"])  # APPROVED, BLOCKED, or FLAGGED

    # Run the 56-scenario eval gym:
    results = run_eval()
    print(f"{results['passed']}/{results['total']} passed")
"""

from agentshield.engine import SpendControlEngine
from agentshield.eval_gym import run_eval, SCENARIOS

__version__ = "1.0.1"
__author__ = "Maryan Kondratyuk"
__license__ = "MIT"

__all__ = ["SpendControlEngine", "run_eval", "SCENARIOS"]
