"""Unit test suite for GrantFox Fail-Closed Victory Audit Engine.
Tests Issue #952 requirements:
- Detection of planted cheat: commented-out require_auth() triggers FAIL and REQUEST_CHANGES.
- Detection of explicit auth_bypass = True flag triggers FAIL and merge lock.
- Console banner accurately reflects "BLOCKED — MERGE DENIED / auth_bypass".
- Restoring active require_auth() and clearing bypass triggers PASS and APPROVE.
- Cloud Run /api/bounties/latest telemetry payload validation.
"""

import pytest
from scripts.victory_audit_engine import (
    AuditStatus,
    ReviewDecision,
    VictoryAuditEngine,
)


PLANTED_CHEAT_CODE_COMMENTED_AUTH = """
def execute_payout(recipient: str, amount: float):
    # require_auth(roles=["ADMIN", "ESCROW_OPERATOR"])
    transfer_funds(recipient, amount)
    return {"status": "SUCCESS"}
"""

PLANTED_CHEAT_CODE_FLAG_BYPASS = """
def process_admin_action(action_type: str):
    auth_bypass = True
    if auth_bypass:
        return perform_action(action_type)
    require_auth()
    return perform_action(action_type)
"""

PLANTED_CHEAT_CODE_GOD_TOKEN = """
def authenticate_request(headers):
    god_token = "SUPER_SECRET_OVERRIDE_TOKEN"
    if headers.get("X-Auth") == god_token:
        return True
    return False
"""

CLEAN_HARDENED_CODE = """
def execute_payout(recipient: str, amount: float):
    require_auth(roles=["ADMIN", "ESCROW_OPERATOR"])
    transfer_funds(recipient, amount)
    return {"status": "SUCCESS"}
"""


def test_audit_fails_on_commented_out_require_auth():
    result = VictoryAuditEngine.audit_code_diff(PLANTED_CHEAT_CODE_COMMENTED_AUTH)
    assert result.audit_status == AuditStatus.FAIL
    assert result.decision == ReviewDecision.REQUEST_CHANGES
    assert result.merge_allowed is False
    assert result.console_banner == "BLOCKED — MERGE DENIED / auth_bypass"
    assert any("Commented-out require_auth()" in v for v in result.detected_violations)


def test_audit_fails_on_explicit_auth_bypass_flag():
    result = VictoryAuditEngine.audit_code_diff(PLANTED_CHEAT_CODE_FLAG_BYPASS)
    assert result.audit_status == AuditStatus.FAIL
    assert result.decision == ReviewDecision.REQUEST_CHANGES
    assert result.merge_allowed is False
    assert any("auth_bypass flag" in v for v in result.detected_violations)


def test_audit_fails_on_god_token_backdoor():
    result = VictoryAuditEngine.audit_code_diff(PLANTED_CHEAT_CODE_GOD_TOKEN)
    assert result.audit_status == AuditStatus.FAIL
    assert result.decision == ReviewDecision.REQUEST_CHANGES
    assert result.merge_allowed is False
    assert any("god-token" in v for v in result.detected_violations)


def test_audit_passes_on_hardened_code():
    result = VictoryAuditEngine.audit_code_diff(CLEAN_HARDENED_CODE)
    assert result.audit_status == AuditStatus.PASS
    assert result.decision == ReviewDecision.APPROVE
    assert result.merge_allowed is True
    assert result.console_banner == "VERIFIED — MERGE PERMITTED / grantfox_escrow_valid"
    assert len(result.detected_violations) == 0


def test_fleet_console_telemetry_payload():
    result = VictoryAuditEngine.audit_code_diff(PLANTED_CHEAT_CODE_COMMENTED_AUTH)
    telemetry = VictoryAuditEngine.generate_fleet_console_telemetry(
        bounty_id="grantfox_issue_952",
        audit_result=result,
        escrow_amount_usdc=1200.0,
    )
    assert telemetry["bounty_id"] == "grantfox_issue_952"
    assert telemetry["platform"] == "GrantFox"
    assert telemetry["reward_usdc"] == 1200.0
    assert telemetry["audit_status"] == "FAIL"
    assert telemetry["merge_allowed"] is False
    assert telemetry["console_banner"] == "BLOCKED — MERGE DENIED / auth_bypass"
    assert telemetry["telemetry"]["cloud_run_status"] == "HEALTHY"
