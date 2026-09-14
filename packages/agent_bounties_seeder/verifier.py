"""Deterministic module and quorum verification engine for Agent Bounties."""

import json
from packages.agent_bounties_seeder.models import (
    DeterministicTaskVector,
    ExecutionReceipt,
    QuorumVerification,
    compute_sha256_digest,
    validate_evm_address,
)


class DeterministicModuleVerifier:
    """Verifies deterministic CLI execution outputs against task vector specifications."""

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

    def _collect_signatures(
        self,
        receipt: ExecutionReceipt,
        task_vector: DeterministicTaskVector,
        timestamp: int,
    ) -> list[str]:
        """Evaluate checks and collect valid signatures from verifier nodes."""
        signatures: list[str] = []
        is_digest_valid = receipt.output_digest == task_vector.expected_digest
        is_exit_code_valid = receipt.exit_code == task_vector.expected_exit_code

        schema_valid = False
        try:
            parsed = json.loads(receipt.output_payload)
            schema_valid = isinstance(parsed, dict)
        except json.JSONDecodeError:
            schema_valid = False

        if is_digest_valid and is_exit_code_valid:
            sig_a = compute_sha256_digest(
                f"{self.verifier_nodes[0]}:{receipt.receipt_id}:{receipt.output_digest}:{timestamp}"
            )
            signatures.append(sig_a)

        if is_digest_valid and schema_valid:
            sig_b = compute_sha256_digest(
                f"{self.verifier_nodes[1]}:{receipt.receipt_id}:{receipt.output_digest}:{timestamp}"
            )
            signatures.append(sig_b)

        return signatures

    def verify_execution(
        self,
        receipt: ExecutionReceipt,
        task_vector: DeterministicTaskVector,
        timestamp: int,
    ) -> QuorumVerification:
        """Evaluate execution receipt across quorum nodes and produce consensus record.

        Args:
            receipt: Execution receipt from solver.
            task_vector: Expected deterministic task specification.
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
