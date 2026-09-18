"""
End-to-end verification script for Issue #1573 solution.
"""

from decimal import Decimal
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from packages.omni_boxy_guard import (
    BoxyReviewBot,
    BoxySettlementEngine,
    Contributor,
    HumorAnalysisEngine,
    HumorClassification,
    PRAction,
    PullRequest,
    WhitelistManager,
)


def run_checks() -> int:
    """Execute comprehensive verification checks across Boxy PR guard and settlement engines.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    sys.stdout.write("Running Issue #1573 Comprehensive Verification...\n")

    wm = WhitelistManager(["verified_partner"])
    assert wm.is_whitelisted("verified_partner") is True
    assert wm.is_whitelisted("outsider") is False

    bot = BoxyReviewBot(whitelist_manager=wm)

    stranger_pr = PullRequest(
        pr_number=1001,
        title="Unsolicited patch",
        description="External changes",
        author=Contributor(username="outsider", organization_member=False),
    )
    stranger_verdict = bot.evaluate_pull_request(stranger_pr)
    assert stranger_verdict.final_action == PRAction.CLOSE
    assert "@OmniBlocks/coders" in stranger_verdict.preemptive_result.target_role_ping

    humor_add_pr = PullRequest(
        pr_number=1002,
        title="Add comedy relief",
        description="Jokes and puns",
        author=Contributor(username="verified_partner", organization_member=False),
        diff="--- a/f.py\n+++ b/f.py\n@@ -1,1 +1,2 @@\n+# rubber duck funny joke haha\n",
    )
    add_verdict = bot.evaluate_pull_request(humor_add_pr)
    assert add_verdict.final_action == PRAction.APPROVE

    humor_strip_pr = PullRequest(
        pr_number=1003,
        title="Clean comments",
        description="Remove humor",
        author=Contributor(username="staff", organization_member=True),
        diff="--- a/f.py\n+++ b/f.py\n@@ -1,2 +1,1 @@\n-# rubber duck funny joke haha\n",
    )
    strip_verdict = bot.evaluate_pull_request(humor_strip_pr)
    assert strip_verdict.final_action == PRAction.REQUEST_CHANGES

    base_q, real_q, bonus_q = BoxySettlementEngine.calculate_issue_1573_quotes()
    assert base_q.net_cash_payout_usd == Decimal("82.80")
    assert real_q.net_cash_payout_usd == Decimal("165.60")
    assert bonus_q.net_cash_payout_usd == Decimal("243.00")

    node_res = subprocess.run(["node", "test/boxy_guard.test.js"], capture_output=True, text=True, check=False)
    if node_res.returncode != 0:
        sys.stderr.write(f"Node.js test failure: {node_res.stderr}\n")
        return 1

    sys.stdout.write("All Issue #1573 verification checks passed successfully.\n")
    return 0


if __name__ == "__main__":
    sys.exit(run_checks())
