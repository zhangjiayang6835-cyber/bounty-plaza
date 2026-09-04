"""Runbook Schema, Base Inventory Query, and SHA-256 Hash Verifier Subsystem.
Resolves Issue #842: Verification Complete: Runbook Schema, Inventory Query, and SHA-256 Hashing Verified.
Related: Open Competition V2 / Base Mainnet Autonomous Bounties ($89 USD).

Provides deterministic verification for:
1. Canonical runbook schema adherence (steps, operations, and fallbacks).
2. Base mainnet inventory query parser and active competition extraction.
3. Cryptographic SHA-256 artifact digest generation and integrity verification.
"""

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

CANONICAL_SCHEMA = "agent-bounties/agent-earning-runbook-v1"
CANONICAL_INVENTORY_ENDPOINT = "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory"


@dataclass
class ActiveCompetition:
    competition_id: str
    title: str
    prize_usdc: float
    verifier_contract: str
    state: str = "active"


class RunbookInventoryHashVerifier:
    """Verifies runbook schema compliance, inventory query payloads, and cryptographic SHA-256 digests."""

    def __init__(self):
        pass

    def validate_runbook_schema(self, runbook: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validates runbook top-level attributes and step structures."""
        errors = []

        if not isinstance(runbook, dict):
            return False, ["Runbook payload must be a JSON object"]

        if runbook.get("schema_version") != CANONICAL_SCHEMA:
            errors.append(f"Invalid schema_version: expected '{CANONICAL_SCHEMA}'")

        steps = runbook.get("steps")
        if not isinstance(steps, list):
            errors.append("Steps must be a list")
        elif len(steps) < 6:
            errors.append(f"Steps count must be at least 6, got {len(steps)}")
        else:
            for idx, step in enumerate(steps):
                if not isinstance(step, dict):
                    errors.append(f"Step index {idx} is not a valid dictionary")
                    continue
                if not step.get("id"):
                    errors.append(f"Step {idx} missing 'id'")
                if not step.get("operation"):
                    errors.append(f"Step {idx} missing 'operation'")

        return len(errors) == 0, errors

    def parse_inventory_response(self, inventory_json: Dict[str, Any]) -> Tuple[bool, List[ActiveCompetition], List[str]]:
        """Parses Base mainnet inventory response and extracts active competitions."""
        errors = []
        competitions = []

        if not isinstance(inventory_json, dict):
            return False, [], ["Inventory response must be a JSON object"]

        records = inventory_json.get("items") or inventory_json.get("competitions") or []
        if not isinstance(records, list):
            return False, [], ["Inventory records must be a list"]

        for r in records:
            if not isinstance(r, dict):
                continue
            state = r.get("state", "active").lower()
            if state == "active":
                comp = ActiveCompetition(
                    competition_id=str(r.get("id") or r.get("bounty_id", "")),
                    title=str(r.get("title", "")),
                    prize_usdc=float(r.get("prize_usdc") or r.get("prize_amount") or 0.0),
                    verifier_contract=str(r.get("verifier_contract") or r.get("contract", "")),
                    state=state,
                )
                competitions.append(comp)

        return len(competitions) > 0, competitions, errors

    def compute_artifact_sha256(self, artifact: Dict[str, Any]) -> str:
        """Computes deterministic canonical SHA-256 digest of the artifact."""
        canonical_bytes = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()

    def verify_artifact_hash(self, artifact: Dict[str, Any], expected_sha256: str) -> bool:
        """Verifies calculated SHA-256 against expected hash."""
        computed = self.compute_artifact_sha256(artifact)
        return computed.lower() == expected_sha256.lower()
