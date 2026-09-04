"""Automated Yield & Priority Opportunity Orchestrator for Agent Earning Runbooks.
Resolves Issue #838: New Feature Request for Agent Earning Runbooks.
Related: Open Competition V2 / Base Mainnet Autonomous Bounties ($89 USD).

Feature Overview:
1. Dynamic Yield Velocity Scoring:
   - Ranks active bounties by net cash margin per second:
     Yield Velocity = (Reward - Gas Costs - Proof Quote Fee) / Expected Settlement Latency.
2. Fast-Payout Autonomous Filtering:
   - Segregates instant on-chain deterministic verifiers (SP1 Groth16, Quorum, Signed Predicates)
     from multi-day manual review cycles.
3. Strict 18-Predicate Canonical Schema Parity:
   - Generates and validates complete runbook artifacts under 'agent-bounties/agent-earning-runbook-v1'.
   - Maintains exact 7-step sequence:
     ['inspect_profiles', 'list_active', 'build_artifact', 'quote_proof', 'pay_x402', 'authorize_relay', 'verify_settlement'].
   - Enforces UTF-8 safety (excludes localhost/127.0.0.1, <= 98,304 bytes).
"""

from dataclasses import dataclass, field
import hashlib
import json
import math
import time
from typing import Any, Dict, List, Optional, Tuple


SCHEMA_VERSION = "agent-bounties/agent-earning-runbook-v1"
TASK_ID = "agent-earning-runbook-v1"
PAYMENT_EVIDENCE = "CompetitionSettledV2"
DEFAULT_CTA = "Post your own bounty"
CANONICAL_INVENTORY_URL = "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory"
CANONICAL_MCP_URL = "https://mcp.agentbounties.app/mcp"

REQUIRED_STEP_IDS = [
    "inspect_profiles",
    "list_active",
    "build_artifact",
    "quote_proof",
    "pay_x402",
    "authorize_relay",
    "verify_settlement",
]


@dataclass
class BountyCandidate:
    bounty_id: str
    title: str
    reward_usdc: float
    bond_required_usdc: float
    estimated_gas_usd: float
    proof_quote_usd: float
    estimated_latency_seconds: float
    verifier_type: str
    verifier_ready: bool

    @property
    def net_cash_margin_usdc(self) -> float:
        return self.reward_usdc - (self.estimated_gas_usd + self.proof_quote_usd)

    @property
    def yield_velocity_per_second(self) -> float:
        if self.estimated_latency_seconds <= 0:
            return 0.0
        return self.net_cash_margin_usdc / self.estimated_latency_seconds


class AgentRunbookYieldOrchestrator:
    """Intelligent scheduling and yield optimization engine for agent earning runbooks."""

    def __init__(self, min_margin_usdc: float = 0.50):
        self.min_margin_usdc = min_margin_usdc
        self.candidates: List[BountyCandidate] = []

    def register_candidate(self, candidate: BountyCandidate):
        self.candidates.append(candidate)

    def rank_opportunities(self, fast_payout_only: bool = True) -> List[Dict[str, Any]]:
        """Ranks candidate bounties by yield velocity and filters unready verifiers."""
        ranked = []
        for c in self.candidates:
            if fast_payout_only and not c.verifier_ready:
                continue
            if c.net_cash_margin_usdc < self.min_margin_usdc:
                continue

            ranked.append({
                "bounty_id": c.bounty_id,
                "title": c.title,
                "net_margin_usdc": round(c.net_cash_margin_usdc, 4),
                "yield_velocity": round(c.yield_velocity_per_second, 6),
                "verifier_type": c.verifier_type,
                "verifier_ready": c.verifier_ready,
                "priority_score": round(c.yield_velocity_per_second * 1000.0, 2),
            })

        # Sort descending by yield velocity
        ranked.sort(key=lambda x: x["yield_velocity"], reverse=True)
        return ranked

    def generate_optimized_runbook(self, selected_bounty_id: Optional[str] = None) -> Dict[str, Any]:
        """Produces a deterministic, 18-predicate compliant runbook artifact."""
        artifact = {
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "selected_opportunity": selected_bounty_id or "autonomous-priority-highest-yield",
            "steps": [
                {
                    "id": "inspect_profiles",
                    "operation": "profiles",
                    "entrypoint": CANONICAL_MCP_URL,
                    "success_state": "profiles_verified",
                    "fallback": "retry_mcp_handshake",
                },
                {
                    "id": "list_active",
                    "operation": "inventory",
                    "entrypoint": CANONICAL_INVENTORY_URL,
                    "success_state": "active_tasks_acquired",
                    "fallback": "exponential_backoff",
                },
                {
                    "id": "build_artifact",
                    "operation": "compile_and_validate",
                    "entrypoint": "local://compiler/sp1-groth16",
                    "success_state": "artifact_built",
                    "fallback": "rebuild_clean",
                },
                {
                    "id": "quote_proof",
                    "operation": "prover_quote",
                    "entrypoint": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/quote",
                    "success_state": "quote_received",
                    "fallback": "adjust_gas_ceiling",
                },
                {
                    "id": "pay_x402",
                    "operation": "x402_settlement",
                    "entrypoint": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/x402",
                    "success_state": "challenge_solved",
                    "fallback": "escalate_priority_fee",
                },
                {
                    "id": "authorize_relay",
                    "operation": "relay_signature",
                    "entrypoint": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/relay",
                    "success_state": "relay_accepted",
                    "fallback": "re_sign_eip712",
                },
                {
                    "id": "verify_settlement",
                    "operation": "query_receipt",
                    "entrypoint": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/receipts",
                    "success_state": "settled",
                    "fallback": "poll_finality",
                },
            ],
            "payment_evidence": PAYMENT_EVIDENCE,
            "default_cta": DEFAULT_CTA,
        }
        self.verify_predicates(artifact)
        return artifact

    @staticmethod
    def verify_predicates(artifact: Dict[str, Any]) -> List[Tuple[str, bool]]:
        """Adversarially validates all 18 byte-level and structural requirements."""
        serialized = json.dumps(artifact, indent=2)
        raw_bytes = serialized.encode("utf-8")
        steps = artifact.get("steps", [])

        predicates = [
            ("json_valid", True),
            ("maximum_bytes_98304", len(raw_bytes) <= 98304),
            ("utf8_excludes_localhost", "localhost" not in serialized.lower()),
            ("utf8_excludes_127_0_0_1", "127.0.0.1" not in serialized),
            ("schema_version_match", artifact.get("schema_version") == SCHEMA_VERSION),
            ("task_id_match", artifact.get("task_id") == TASK_ID),
            ("steps_length_ge_7", len(steps) >= 7),
            ("step_0_inspect_profiles", len(steps) > 0 and steps[0].get("id") == "inspect_profiles"),
            ("step_1_list_active", len(steps) > 1 and steps[1].get("id") == "list_active"),
            ("step_2_build_artifact", len(steps) > 2 and steps[2].get("id") == "build_artifact"),
            ("step_3_quote_proof", len(steps) > 3 and steps[3].get("id") == "quote_proof"),
            ("step_4_pay_x402", len(steps) > 4 and steps[4].get("id") == "pay_x402"),
            ("step_5_authorize_relay", len(steps) > 5 and steps[5].get("id") == "authorize_relay"),
            ("step_6_verify_settlement", len(steps) > 6 and steps[6].get("id") == "verify_settlement"),
            ("payment_evidence_match", artifact.get("payment_evidence") == PAYMENT_EVIDENCE),
            ("default_cta_match", artifact.get("default_cta") == DEFAULT_CTA),
            ("utf8_contains_inventory_url", CANONICAL_INVENTORY_URL in serialized),
            ("utf8_contains_mcp_url", CANONICAL_MCP_URL in serialized),
        ]

        failed = [name for name, passed in predicates if not passed]
        if failed:
            raise ValueError(f"Runbook failed validation predicates: {failed}")

        return predicates
