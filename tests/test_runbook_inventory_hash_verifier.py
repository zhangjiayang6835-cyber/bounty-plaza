"""Unit tests for Runbook Schema, Base Inventory Query, and SHA-256 Hash Verifier Subsystem.
Resolves Issue #842 ($89 USD).
"""

import hashlib
import json
import unittest
from scripts.runbook_inventory_hash_verifier import (
    ActiveCompetition,
    RunbookInventoryHashVerifier,
    CANONICAL_SCHEMA,
)


class TestRunbookInventoryHashVerifier(unittest.TestCase):
    def setUp(self):
        self.verifier = RunbookInventoryHashVerifier()

    def test_validate_valid_runbook_schema(self):
        runbook = {
            "schema_version": CANONICAL_SCHEMA,
            "task_id": "agent-earning-runbook-v1",
            "steps": [
                {"id": "inspect_profiles", "operation": "profiles"},
                {"id": "list_active", "operation": "inventory"},
                {"id": "build_artifact", "operation": "prepare_profile"},
                {"id": "quote_proof", "operation": "quote_proof"},
                {"id": "pay_x402", "operation": "pay_proof_job"},
                {"id": "verify_settlement", "operation": "events"},
            ],
        }
        valid, errors = self.verifier.validate_runbook_schema(runbook)
        self.assertTrue(valid, f"Unexpected errors: {errors}")
        self.assertEqual(len(errors), 0)

    def test_reject_schema_with_fewer_than_six_steps(self):
        runbook = {
            "schema_version": CANONICAL_SCHEMA,
            "steps": [
                {"id": "step1", "operation": "op1"},
                {"id": "step2", "operation": "op2"},
            ],
        }
        valid, errors = self.verifier.validate_runbook_schema(runbook)
        self.assertFalse(valid)
        self.assertTrue(any("at least 6" in err for err in errors))

    def test_parse_base_inventory_response(self):
        inventory_data = {
            "network": "base-mainnet",
            "items": [
                {"id": "comp-1", "title": "Base Fast Bounty 1", "prize_usdc": 89.0, "contract": "0x123", "state": "active"},
                {"id": "comp-2", "title": "Base Fast Bounty 2", "prize_usdc": 99.0, "contract": "0x456", "state": "active"},
                {"id": "comp-3", "title": "Base Fast Bounty 3", "prize_usdc": 50.0, "contract": "0x789", "state": "active"},
                {"id": "comp-4", "title": "Base Fast Bounty 4", "prize_usdc": 89.0, "contract": "0xabc", "state": "active"},
                {"id": "comp-5", "title": "Base Fast Bounty 5", "prize_usdc": 120.0, "contract": "0xdef", "state": "active"},
                {"id": "comp-6", "title": "Expired Bounty", "prize_usdc": 10.0, "contract": "0x000", "state": "settled"},
            ]
        }
        success, comps, errors = self.verifier.parse_inventory_response(inventory_data)
        self.assertTrue(success)
        self.assertEqual(len(comps), 5)
        self.assertEqual(comps[0].competition_id, "comp-1")
        self.assertEqual(comps[0].prize_usdc, 89.0)

    def test_compute_and_verify_artifact_sha256(self):
        artifact = {
            "schema_version": CANONICAL_SCHEMA,
            "task_id": "test-task",
            "proof_quote": 0.10,
        }
        expected_digest = hashlib.sha256(
            json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        computed = self.verifier.compute_artifact_sha256(artifact)
        self.assertEqual(computed, expected_digest)
        self.assertTrue(self.verifier.verify_artifact_hash(artifact, expected_digest))
        self.assertFalse(self.verifier.verify_artifact_hash(artifact, "invalid_hash"))


if __name__ == "__main__":
    unittest.main()
