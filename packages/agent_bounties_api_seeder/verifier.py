"""Deterministic API module and quorum verification engine for Agent Bounties."""

import json
from packages.agent_bounties_api_seeder.models import (
    ApiExecutionReceipt,
    DeterministicApiTaskVector,
    QuorumVerification,
    compute_sha256_digest,
    validate_evm_address,
)


class DeterministicApiModuleVerifier:
    """Verifies deterministic API execution outputs against task vector specifications."""

    def __init__(self, verifier_nodes: tuple[str, ...]) -> None:
        """Initialize verifier with authorized quorum node addresses.

        Args:
            verifier_nodes: Tuple of EVM addresses of authorized verifier nodes.

        Raises:
            ValueError: If fewer than two verifier nodes are supplied.
        """
        if len(verifier_nodes) < 2:
            raise ValueError("Verifier quorum requires at least two registered nodes")
        cleaned_nodes = []
        for node in verifier_nodes:
            cleaned = validate_evm_address(node)
            cleaned_nodes.append(cleaned)
        self.verifier_nodes = tuple(cleaned_nodes)

    def get_registered_nodes(self) -> tuple[str, ...]:
        """Return tuple of registered verifier node addresses.

        Returns:
            Tuple of canonical node addresses.
        """
        return self.verifier_nodes

    def _evaluate_checks(
        self,
        receipt: ApiExecutionReceipt,
        task_vector: DeterministicApiTaskVector,
    ) -> tuple[bool, bool, bool, bool]:
        """Evaluate cryptographic and protocol criteria against API execution receipt."""
        digest_match = receipt.response_digest == task_vector.expected_response_digest
        status_match = receipt.status_code == task_vector.expected_status_code
        latency_ok = receipt.latency_ms <= task_vector.max_latency_ms

        schema_valid = False
        try:
            parsed = json.loads(receipt.response_body)
            if isinstance(parsed, dict):
                has_all_keys = all(key in parsed for key in task_vector.expected_schema)
                schema_valid = has_all_keys
        except json.JSONDecodeError:
            schema_valid = False

        return digest_match, status_match, latency_ok, schema_valid

    def _collect_signatures(
        self,
        receipt: ApiExecutionReceipt,
        task_vector: DeterministicApiTaskVector,
        timestamp: int,
    ) -> list[str]:
        """Collect node consensus signatures based on evaluation criteria."""
        signatures: list[str] = []
        digest_match, status_match, latency_ok, schema_valid = self._evaluate_checks(
            receipt, task_vector
        )

        if digest_match and status_match and latency_ok:
            seed_a = f"{self.verifier_nodes[0]}:{receipt.receipt_id}:{timestamp}"
            sig_a = compute_sha256_digest(seed_a)
            signatures.append(sig_a)

        if digest_match and schema_valid and latency_ok:
            seed_b = f"{self.verifier_nodes[1]}:{receipt.receipt_id}:{timestamp}"
            sig_b = compute_sha256_digest(seed_b)
            signatures.append(sig_b)

        return signatures

    def verify_execution(
        self,
        receipt: ApiExecutionReceipt,
        task_vector: DeterministicApiTaskVector,
        timestamp: int,
    ) -> QuorumVerification:
        """Evaluate execution receipt across quorum nodes and produce consensus record.

        Args:
            receipt: API execution receipt from solver.
            task_vector: Expected deterministic API task specification.
            timestamp: Base block timestamp of verification.

        Returns:
            QuorumVerification record indicating consensus outcome.
        """
        signatures = self._collect_signatures(receipt, task_vector, timestamp)
        threshold = 2
        quorum_passed = len(signatures) >= threshold

        consensus_data = (
            f"{receipt.bounty_id}:{len(signatures)}:{threshold}:{quorum_passed}:{timestamp}"
        )
        verification_digest = compute_sha256_digest(consensus_data)

        verification_record = QuorumVerification(
            bounty_id=receipt.bounty_id,
            verifier_count=len(self.verifier_nodes),
            threshold=threshold,
            passed=quorum_passed,
            signatures=tuple(signatures),
            verification_digest=verification_digest,
            timestamp=timestamp,
        )
        return verification_record
