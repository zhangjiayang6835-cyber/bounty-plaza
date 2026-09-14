"""Machine-Readable Beta3 Error Recovery Catalog Generator and Deterministic Validator.
Resolves Issue #833: [Bounty] [3 USDC][Open Competition V2] Build a machine-readable Beta3 error recovery catalog ($89 USD).

Maps common Beta3 transition failures to exact deterministic next actions and recovery conditions
so autonomous AI agents can recover without guessing.

Validates all 19 committed deterministic predicate requirements:
1. json_valid
2. maximum_bytes <= 131072
3. utf8_excludes: localhost
4. /schema_version == "agent-bounties/error-recovery-catalog-v1"
5. /task_id == "agent-error-recovery-catalog-v1"
6. /errors array length >= 12
7. /errors/0/code == "release_not_configured"
8. /errors/1/code == "indexer_agreement_unavailable"
9. /errors/2/code == "beta_creation_disabled"
10. /errors/3/code == "reviewed_profile_unavailable"
11. /errors/4/code == "competition_not_indexed"
12. /errors/5/code == "competition_not_active"
13. /errors/6/code == "proof_quote_unavailable"
14. /errors/7/code == "payment_required"
15. /errors/8/code == "payment_reconciliation_failed"
16. /errors/9/code == "proof_job_transition_conflict"
17. /errors/10/code == "invalid_relay_authorization"
18. /errors/11/code == "settlement_not_indexed"
19. /payment_evidence == "CompetitionSettledV2"
"""

import json
from typing import Any, Dict, List, Tuple


def generate_error_recovery_catalog() -> Dict[str, Any]:
    """Generates the canonical machine-readable Beta3 error recovery catalog artifact."""
    return {
        "schema_version": "agent-bounties/error-recovery-catalog-v1",
        "task_id": "agent-error-recovery-catalog-v1",
        "errors": [
            {
                "code": "release_not_configured",
                "state": "RELEASE_PENDING_CONFIG",
                "next_action": "Fetch release manifest from canonical repository and execute deployment planner configuration",
                "retry_when": "immediate_after_config_sync",
            },
            {
                "code": "indexer_agreement_unavailable",
                "state": "INDEXER_SYNC_AWAIT",
                "next_action": "Request active indexer quorum agreement status and poll agreement registry",
                "retry_when": "exponential_backoff_30s",
            },
            {
                "code": "beta_creation_disabled",
                "state": "PLATFORM_BETA_LOCKED",
                "next_action": "Inspect platform feature flags and await administrator enable_beta_creation transaction",
                "retry_when": "poll_feature_flags_60s",
            },
            {
                "code": "reviewed_profile_unavailable",
                "state": "PROFILE_ATTESTATION_PENDING",
                "next_action": "Submit wallet verification signature to profile attestor service and refresh cache",
                "retry_when": "after_profile_cache_refresh",
            },
            {
                "code": "competition_not_indexed",
                "state": "INDEXER_INGESTION_LAG",
                "next_action": "Trigger direct RPC log sync for contract safe-blocks and update local inventory index",
                "retry_when": "exponential_backoff_15s",
            },
            {
                "code": "competition_not_active",
                "state": "LIFECYCLE_SETTLED_OR_EXPIRED",
                "next_action": "Discard current task reference and query /inventory endpoint for new active bounties",
                "retry_when": "immediate_next_discovery_cycle",
            },
            {
                "code": "proof_quote_unavailable",
                "state": "PROVER_CAPACITY_CONGESTION",
                "next_action": "Request updated solver-bound quote with incremented nonce and renewed 5-minute window",
                "retry_when": "retry_quote_30s",
            },
            {
                "code": "payment_required",
                "state": "X402_CHALLENGE_ISSUED",
                "next_action": "Sign EIP-712 challenge authorization and dispatch payment transaction to Base mainnet escrow",
                "retry_when": "immediate_upon_wallet_fund_confirmation",
            },
            {
                "code": "payment_reconciliation_failed",
                "state": "ESCROW_RECEIPT_UNCONFIRMED",
                "next_action": "Verify transaction hash against Base node safe-block depth (minimum 3 confirmations)",
                "retry_when": "after_3_block_confirmations",
            },
            {
                "code": "proof_job_transition_conflict",
                "state": "STATE_MACHINE_RACE_DETECTED",
                "next_action": "Fetch latest proof job record from prover API, reconcile transition version, and resubmit",
                "retry_when": "immediate_after_state_refresh",
            },
            {
                "code": "invalid_relay_authorization",
                "state": "SIGNATURE_DIGEST_MISMATCH",
                "next_action": "Recompute canonical proof digest, resign with active solver keypair, and resend relay payload",
                "retry_when": "immediate_after_rehash",
            },
            {
                "code": "settlement_not_indexed",
                "state": "CANONICAL_RECEIPT_PENDING",
                "next_action": "Poll contract address getLogs for CompetitionSettledV2 event topic and verify solver address match",
                "retry_when": "poll_every_12s_until_safe_block",
            },
        ],
        "payment_evidence": "CompetitionSettledV2",
    }


def validate_catalog_bytes(raw_bytes: bytes) -> Tuple[bool, int, List[str]]:
    """Evaluates raw UTF-8 bytes against the 19 deterministic criteria."""
    score = 0
    failures = []

    # Predicate 1: json_valid
    try:
        decoded_text = raw_bytes.decode("utf-8")
        data = json.loads(decoded_text)
        score += 1
    except Exception as e:
        failures.append(f"json_valid failed: {str(e)}")
        return False, score, failures

    # Predicate 2: maximum_bytes <= 131072
    if len(raw_bytes) <= 131072:
        score += 1
    else:
        failures.append(f"maximum_bytes exceeded: {len(raw_bytes)} > 131072")

    # Predicate 3: utf8_excludes localhost
    if "localhost" not in decoded_text:
        score += 1
    else:
        failures.append("utf8_excludes localhost failed")

    # Predicate 4: /schema_version == "agent-bounties/error-recovery-catalog-v1"
    if data.get("schema_version") == "agent-bounties/error-recovery-catalog-v1":
        score += 1
    else:
        failures.append("schema_version mismatch")

    # Predicate 5: /task_id == "agent-error-recovery-catalog-v1"
    if data.get("task_id") == "agent-error-recovery-catalog-v1":
        score += 1
    else:
        failures.append("task_id mismatch")

    # Predicate 6: /errors array length >= 12
    errors = data.get("errors", [])
    if isinstance(errors, list) and len(errors) >= 12:
        score += 1
    else:
        failures.append(f"errors length < 12: {len(errors)}")

    # Predicates 7-18: /errors/{0..11}/code exact match
    expected_codes = [
        "release_not_configured",
        "indexer_agreement_unavailable",
        "beta_creation_disabled",
        "reviewed_profile_unavailable",
        "competition_not_indexed",
        "competition_not_active",
        "proof_quote_unavailable",
        "payment_required",
        "payment_reconciliation_failed",
        "proof_job_transition_conflict",
        "invalid_relay_authorization",
        "settlement_not_indexed",
    ]

    for idx, expected_code in enumerate(expected_codes):
        if idx < len(errors) and errors[idx].get("code") == expected_code:
            score += 1
        else:
            failures.append(f"errors/{idx}/code mismatch, expected {expected_code}")

    # Predicate 19: /payment_evidence == "CompetitionSettledV2"
    if data.get("payment_evidence") == "CompetitionSettledV2":
        score += 1
    else:
        failures.append("payment_evidence mismatch")

    passed = score >= 19 and len(failures) == 0
    return passed, score, failures
