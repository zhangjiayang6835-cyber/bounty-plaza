"""Unit tests for Deterministic Agent Earning Runbook Fix Engine.
Resolves Issue #839: Fix for [Bounty] Write the shortest deterministic agent earning run.
Validates automated repair, byte minimization, and 18-predicate compliance.
"""

import json
import unittest
from scripts.fix_script import (
    RunbookFixEngine,
    fix_and_verify_runbook,
    CANONICAL_SCHEMA,
    CANONICAL_TASK_ID,
    PAYMENT_EVIDENCE,
    DEFAULT_CTA,
)


class TestRunbookFixEngine(unittest.TestCase):
    def setUp(self):
        self.engine = RunbookFixEngine()

    def test_default_repair_produces_fully_valid_artifact(self):
        repaired, raw, valid, score = fix_and_verify_runbook()
        self.assertTrue(valid)
        self.assertEqual(score, 18)
        self.assertLessEqual(len(raw), 98304)

    def test_repair_malformed_input_replaces_invalid_steps_and_fields(self):
        malformed = {
            "schema_version": "corrupted-version",
            "task_id": "invalid-task",
            "steps": [
                {"id": "wrong_first_step", "operation": "unknown"},
                {"id": "build_artifact", "operation": "prepare_profile"},
            ],
            "payment_evidence": "wrong_evidence",
        }
        repaired = self.engine.repair_runbook(malformed)
        self.assertEqual(repaired["schema_version"], CANONICAL_SCHEMA)
        self.assertEqual(repaired["task_id"], CANONICAL_TASK_ID)
        self.assertEqual(repaired["payment_evidence"], PAYMENT_EVIDENCE)
        self.assertEqual(repaired["default_cta"], DEFAULT_CTA)
        self.assertEqual(len(repaired["steps"]), 7)
        self.assertEqual(repaired["steps"][0]["id"], "inspect_profiles")
        self.assertEqual(repaired["steps"][6]["id"], "verify_settlement")

        raw_bytes = self.engine.serialize_minimal_bytes(repaired)
        valid, score, failures = self.engine.audit_predicates(raw_bytes)
        self.assertTrue(valid, f"Failures: {failures}")
        self.assertEqual(score, 18)

    def test_localhost_and_loopback_sanitization(self):
        malformed = {
            "steps": [
                {"id": "inspect_profiles", "entrypoint": "http://localhost:8080/mcp"},
                {"id": "list_active", "entrypoint": "http://127.0.0.1:3000/inventory"},
            ]
        }
        repaired = self.engine.repair_runbook(malformed)
        raw_bytes = self.engine.serialize_minimal_bytes(repaired)
        text = raw_bytes.decode("utf-8")
        self.assertNotIn("localhost", text)
        self.assertNotIn("127.0.0.1", text)
        valid, score, failures = self.engine.audit_predicates(raw_bytes)
        self.assertTrue(valid)
        self.assertEqual(score, 18)

    def test_audit_predicates_catches_oversized_payload(self):
        valid_artifact = self.engine.repair_runbook()
        oversized_artifact = dict(valid_artifact)
        oversized_artifact["junk_padding"] = "x" * 100000
        raw_oversized = self.engine.serialize_minimal_bytes(oversized_artifact)
        valid, score, failures = self.engine.audit_predicates(raw_oversized)
        self.assertFalse(valid)
        self.assertTrue(any("byte_limit_exceeded" in f for f in failures))


if __name__ == "__main__":
    unittest.main()
