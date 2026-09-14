"""Deterministic module verifier modeling Base decentralized verifier quorum."""

from typing import Sequence
from packages.wallet_ux_seeder.models import (
    ExecutionReceipt,
    QuorumVerification,
    WalletUXTaskVector,
    compute_sha256_digest,
    validate_evm_address,
)

DEFAULT_VERIFIER_NODES = (
    "0x380c1af742593dd88b6f20387e9ee693a0536731",
    "0x1518ccd19002ca3b69dc33aa4ade349f70be6446",
)


class DeterministicModuleVerifier:
    """Verifier executing consensus evaluation across verifier node registry."""

    def __init__(
        self,
        verifier_nodes: Sequence[str] = DEFAULT_VERIFIER_NODES,
        threshold: int = 2,
    ) -> None:
        """Initialize verifier quorum with authorized node addresses.

        Args:
            verifier_nodes: Sequence of authorized EVM verifier addresses.
            threshold: Minimum agreeing node count for quorum consensus.

        Raises:
            ValueError: If threshold is invalid for node count.
        """
        validated_nodes = [validate_evm_address(addr) for addr in verifier_nodes]
        if len(set(validated_nodes)) < len(validated_nodes):
            raise ValueError("Verifier nodes must be distinct")
        if threshold <= 0 or threshold > len(validated_nodes):
            raise ValueError("Threshold must be positive and not exceed node count")

        self.nodes = tuple(validated_nodes)
        self.threshold = threshold

    def is_authorized_node(self, address: str) -> bool:
        """Check whether an EVM address belongs to the authorized verifier quorum.

        Args:
            address: EVM address to inspect.

        Returns:
            True if address is in node set, False otherwise.
        """
        canonical = validate_evm_address(address)
        is_member = canonical in self.nodes
        return is_member

    def verify_execution(
        self,
        receipt: ExecutionReceipt,
        task_vector: WalletUXTaskVector,
        timestamp: int,
    ) -> QuorumVerification:
        """Evaluate execution receipt against deterministic wallet UX task vector.

        Args:
            receipt: Execution receipt containing output and exit code.
            task_vector: Expected execution specifications.
            timestamp: Verification block timestamp.

        Returns:
            QuorumVerification consensus record.
        """
        matches_exit = receipt.exit_code == task_vector.expected_exit_code
        matches_digest = receipt.output_digest == task_vector.expected_digest

        valid_execution = matches_exit and matches_digest
        signatures: list[str] = []

        if valid_execution:
            for node in self.nodes:
                sig_material = f"{node}:{receipt.bounty_id}:{receipt.output_digest}:{timestamp}"
                node_signature = compute_sha256_digest(sig_material)
                signatures.append(node_signature)

        passed = len(signatures) >= self.threshold
        digest_material = f"{receipt.bounty_id}:{passed}:{timestamp}:{len(signatures)}"
        verification_digest = f"0x{compute_sha256_digest(digest_material)}"

        verification = QuorumVerification(
            bounty_id=receipt.bounty_id,
            verifier_count=len(self.nodes),
            threshold=self.threshold,
            passed=passed,
            signatures=tuple(signatures),
            verification_digest=verification_digest,
            timestamp=timestamp,
        )
        return verification
