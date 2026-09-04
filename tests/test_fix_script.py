"""Unit tests for Deterministic Agent Earning Runbook Resolution & Auto-Fix Engine.
Resolves Issue #836: Fix for [Bounty] Write the shortest deterministic agent earning run.
"""

import json
import unittest
from scripts.fix_script import (
    DeterministicRunbookFixer,
    build_optimal_runbook,
    CANONICAL_SCHEMA,
    CANONICAL_TASK_ID,
    PAYMENT_EVIDENCE,
    DEFAULT_CTA,
    MAX_ALLOWED_BYTES,
)


class TestDeterministicRunbookFixer(unittest.TestCase):
    def setUp(self):
        self.fixer = DeterministicRunbookFixer()

    def test_optimal_runbook_validates_18_rules(self):
        runbook = build_optimal_runbook()
        payload = self.fixer.serialize_bytes(runbook)
        self.assertLessEqual(len(payload), MAX_ALLOWED_BYTES)

        valid, score, errors = self.fixer.audit(payload)
        self.assertTrue(valid, f"Errors encountered: {errors}")
        self.assertEqual(score, 18)

    def test_repair_normalizes_corrupted_data(self):
        corrupted = {
            "schema_version": "corrupted",
            "task_id": "bad_id",
            "steps": [
                {"id": "unknown_step", "operation": "test"},
                {"id": "inspect_profiles", "entrypoint": "http://localhost:8000"},
            ],
            "payment_evidence": "none",
        }
        repaired = self.fixer.repair(corrupted)
        self.assertEqual(repaired["schema_version"], CANONICAL_SCHEMA)
        self.assertEqual(repaired["task_id"], CANONICAL_TASK_ID)
        self.assertEqual(repaired["payment_evidence"], PAYMENT_EVIDENCE)
        self.assertEqual(repaired["default_cta"], DEFAULT_CTA)
        self.assertEqual(len(repaired["steps"]), 7)

        payload = self.fixer.serialize_bytes(repaired)
        text = payload.decode("utf-8")
        self.assertNotIn("localhost", text)
        self.assertNotIn("127.0.0.1", text)

        valid, score, errors = self.fixer.audit(payload)
        self.assertTrue(valid, f"Errors: {errors}")
        self.assertEqual(score, 18)

    def test_oversized_payload_rejected(self):
        runbook = build_optimal_runbook()
        runbook["filler"] = "a" * (MAX_ALLOWED_BYTES + 100)
        payload = self.fixer.serialize_bytes(runbook)
        valid, score, errors = self.fixer.audit(payload)
        self.assertFalse(valid)
        self.assertIn("byte_limit_exceeded", errors)


if __name__ == "__main__":
    unittest.main()
