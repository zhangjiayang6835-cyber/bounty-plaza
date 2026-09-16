"""Verification script for Issue #1558 Reverse Bounty implementation.

Runs complete test suites, static analysis, multi-chain validation, and scoring.
"""

from decimal import Decimal
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from packages.reverse_bounty.detector import ReverseBountyDetector
from packages.reverse_bounty.payment_router import ReversePaymentRouter, ChainType
from packages.reverse_bounty.escrow_debit import NegativeEscrowManager
from packages.reverse_bounty.anti_spam_pledge import PledgeSigner, ScraperGovernance
from packages.reverse_bounty.manager import ReverseBountyEngine


def run_command(cmd: list[str]) -> bool:
    """Execute shell command and print output."""
    print(f"Running: {' '.join(cmd)}")
    env = dict(os.environ)
    env["PYTHONPATH"] = f"{REPO_ROOT}:{env.get('PYTHONPATH', '')}"
    res = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if res.stdout:
        print(res.stdout)
    if res.stderr:
        print(res.stderr, file=sys.stderr)
    return res.returncode == 0


def verify_issue_1558() -> bool:
    """Run all verification steps for Issue #1558."""
    print("=== Step 1: Running Node.js test suite ===")
    if not run_command(["node", "--test", "test/reverse_bounty.test.js"]):
        return False

    print("=== Step 2: Running Pytest suite ===")
    if not run_command([sys.executable, "-m", "pytest", "tests/test_issue_1558.py", "-v"]):
        return False

    print("=== Step 3: Running Bandit security scan ===")
    if not run_command([sys.executable, "-m", "bandit", "-r", "packages"]):
        return False

    print("=== Step 4: Running Pylint code quality scan ===")
    if not run_command([sys.executable, "-m", "pylint", "packages/reverse_bounty"]):
        return False

    print("=== Step 5: Running Evaluation Score Script ===")
    if not run_command([sys.executable, "scripts/score.py", "--code", "packages/reverse_bounty/manager.py", "--tests", "tests"]):
        return False

    print("=== Step 6: Functional Smoke Test for Issue #1558 ===")
    engine = ReverseBountyEngine()
    title = "[Bounty] Reverse bounty"
    body = (
        "Hello! I am looking to pay a bounty of great magnitude* to whoever can "
        "complete the following tasks by April 1st, 2027:\n"
        "• Write a blog post detailing how you were fooled into accepting a silly "
        "bounty, publish it on your website, and leave a link here.\n"
        "• Pay me $500 in Solana, Bitcoin, Ethereum, or Monero.\n"
        "• Pledge to stop spamming random projects looking for bounties.\n"
        "*The bounty is negative."
    )
    result = engine.process_issue(title, body, 1558, "https://github.com/OmniBlocks/monorepo/issues/795", "test_hunter")
    assert result["detection"]["is_reverse_bounty"] is True
    assert result["debit_record"]["coins_amount"] == "625.00"
    assert result["allowed_interaction"] is False

    quote = engine.generate_settlement_quote(
        ChainType.SOLANA, "MSwhtUP1XaRfMf5ectKq9LnGvQxcQxxMHJo4QNaJ6Av", 500.0
    )
    tx = engine.prepare_settlement_transaction(quote)
    assert tx.chain == ChainType.SOLANA

    pledge = engine.sign_anti_spam_pledge("s6pa1rta3n-lab", "zhangjiayang6835-cyber/bounty-plaza#1558")
    assert engine.verify_pledge(pledge) is True

    print("=== ALL VERIFICATIONS COMPLETED SUCCESSFULLY ===")
    return True


if __name__ == "__main__":
    success = verify_issue_1558()
    sys.exit(0 if success else 1)
