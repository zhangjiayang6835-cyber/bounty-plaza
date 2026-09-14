"""Deterministic MCP module and quorum verification engine for Agent Bounties."""

import json
from packages.agent_bounties_mcp_seeder.models import (
    DeterministicMcpTaskVector,
    McpExecutionReceipt,
    QuorumVerification,
    compute_sha256_digest,
    validate_evm_address,
)


class DeterministicMcpModuleVerifier:
    """Verifies deterministic MCP execution outputs against task vector specifications."""

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
        receipt: McpExecutionReceipt,
        task_vector: DeterministicMcpTaskVector,
    ) -> tuple[bool, bool, bool, bool, bool]:
        """Evaluate cryptographic and protocol criteria against MCP execution receipt."""
        tool_match = receipt.tool_name == task_vector.tool_name
        no_error = not receipt.is_error
        digest_match = receipt.response_digest == task_vector.expected_response_digest
        latency_ok = receipt.latency_ms <= task_vector.max_latency_ms

        content_valid = False
        try:
            parsed = json.loads(receipt.response_content)
            if isinstance(parsed, dict):
                has_all_keys = all(key in parsed for key in task_vector.expected_schema_keys)
                raw_text = str(parsed.get("text", parsed.get("result", "")))
                matches_text = task_vector.expected_text in raw_text
                matches_exact = parsed.get("text") == task_vector.expected_text
                content_valid = has_all_keys and (matches_text or matches_exact)
        except json.JSONDecodeError:
            content_valid = False

        return tool_match, no_error, digest_match, latency_ok, content_valid

    def _collect_signatures(
        self,
        receipt: McpExecutionReceipt,
        task_vector: DeterministicMcpTaskVector,
        timestamp: int,
    ) -> list[str]:
        """Collect node consensus signatures based on evaluation criteria."""
        signatures: list[str] = []
        tool_match, no_error, digest_match, latency_ok, content_valid = self._evaluate_checks(
            receipt, task_vector
        )

        if tool_match and no_error and digest_match and latency_ok:
            seed_a = f"{self.verifier_nodes[0]}:{receipt.receipt_id}:{timestamp}"
            sig_a = compute_sha256_digest(seed_a)
            signatures.append(sig_a)

        if tool_match and no_error and content_valid and latency_ok:
            seed_b = f"{self.verifier_nodes[1]}:{receipt.receipt_id}:{timestamp}"
            sig_b = compute_sha256_digest(seed_b)
            signatures.append(sig_b)

        return signatures

    def verify_execution(
        self,
        receipt: McpExecutionReceipt,
        task_vector: DeterministicMcpTaskVector,
        timestamp: int,
    ) -> QuorumVerification:
        """Evaluate execution receipt across quorum nodes and produce consensus record.

        Args:
            receipt: MCP execution receipt from solver.
            task_vector: Expected deterministic MCP task specification.
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
