"""Orchestrator for Agent Bounties API child bounty lifecycle on Base network."""

import sys
from typing import Optional
from packages.api_child_bounty_seeder.models import (
    APITaskVector,
    BlockAnchor,
    BountyEconomics,
    BountyStatus,
    CanonicalSettlementReceipt,
    ChildBountySpec,
    EconomicMarginAnalysis,
    ExecutionReceipt,
    ParentProofPayload,
    Participant,
    ParticipantRole,
    QuorumVerification,
    abi_encode_address,
    compute_sha256_digest,
    validate_bounty_id,
    validate_evm_address,
)
from packages.api_child_bounty_seeder.verifier import DeterministicModuleVerifier

DEFAULT_EVM_PAYOUT = "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89"
DEFAULT_STELLAR_PAYOUT = "GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC"
DEFAULT_PARENT_CONTRACT = "0xbe17ef2d154265ebe3142d7bda5e99610d571455"
DEFAULT_PARENT_BOUNTY_ID = "0x99f668fc2f432e156033fd2fda2c9e91edffa30cc598013b4f2aaebbfd2348e3"
DEFAULT_CHILD_BOUNTY_ID = "0xa8f37b9215091c6e61f25e98b04a80693a20147b"


class BountyRegistry:
    """In-memory registry tracking participant identities and bounty lifecycle states."""

    def __init__(self) -> None:
        """Initialize empty registry mappings."""
        self.participants: dict[str, Participant] = {}
        self.bounties: dict[str, ChildBountySpec] = {}
        self.bounty_states: dict[str, BountyStatus] = {}
        self.bounty_funders: dict[str, str] = {}
        self.funding_timestamps: dict[str, int] = {}
        self.publication_timestamps: dict[str, int] = {}
        self.claim_timestamps: dict[str, int] = {}
        self.bounty_solvers: dict[str, str] = {}
        self.settlement_receipts: dict[str, CanonicalSettlementReceipt] = {}

    def get_funding_timestamp(self, bounty_id: str) -> int:
        """Retrieve funding timestamp for a given bounty.

        Args:
            bounty_id: Child bounty address.

        Returns:
            Timestamp of funding confirmation.
        """
        ts_val = self.funding_timestamps.get(bounty_id, 0)
        return ts_val

    def is_bounty_funded(self, bounty_id: str) -> bool:
        """Check whether child bounty has achieved funded status.

        Args:
            bounty_id: Child bounty address.

        Returns:
            True if bounty state is ready to earn or later.
        """
        state = self.bounty_states.get(bounty_id)
        is_ready = state in (
            BountyStatus.READY_TO_EARN,
            BountyStatus.EXCLUSIVE_CLAIM,
            BountyStatus.SETTLED,
        )
        return is_ready


class APIBountySeeder:
    """Autonomous seeder and coordinator for child API coding bounties."""

    def __init__(self, verifier: Optional[DeterministicModuleVerifier] = None) -> None:
        """Initialize bounty seeder with deterministic module verifier.

        Args:
            verifier: Verifier instance or None to construct default quorum.
        """
        self.registry = BountyRegistry()
        self.verifier = verifier if verifier is not None else DeterministicModuleVerifier()

    def register_participant(
        self,
        address: str,
        role: ParticipantRole,
        timestamp: int,
    ) -> Participant:
        """Register a participant identity on Base L2 network.

        Args:
            address: 20-byte EVM hex address.
            role: Participant role assignment.
            timestamp: Block timestamp of registration.

        Returns:
            Participant registration object.

        Raises:
            ValueError: If address format is invalid or role conflicts with existing.
        """
        canonical_addr = validate_evm_address(address)
        if canonical_addr in self.registry.participants:
            existing = self.registry.participants[canonical_addr]
            if existing.role != role:
                raise ValueError(
                    f"Participant {canonical_addr} already registered with role {existing.role}"
                )
            return existing

        participant = Participant(
            address=canonical_addr,
            role=role,
            registration_timestamp=timestamp,
            active=True,
        )
        self.registry.participants[canonical_addr] = participant
        return participant

    def publish_child_terms(
        self,
        parent_bounty_id: str,
        title: str,
        description: str,
        reward_usdc: float = 0.90,
        bond_usdc: float = 0.10,
        deadline_timestamp: int = 1791676800,
        verifier_type: str = "deterministic_module",
        child_bounty_id: str = DEFAULT_CHILD_BOUNTY_ID,
        timestamp: int = 1728000000,
    ) -> ChildBountySpec:
        """Publish child bounty specification bound to upstream parent contract.

        Args:
            parent_bounty_id: Upstream parent contract identifier.
            title: Title for child coding task.
            description: Description of requirements and verifier module.
            reward_usdc: Solver completion reward.
            bond_usdc: Required entry/claim bond.
            deadline_timestamp: Funding and execution deadline.
            verifier_type: Module verifier identifier.
            child_bounty_id: EVM address for child contract.
            timestamp: Terms publication timestamp.

        Returns:
            ChildBountySpec object.
        """
        validate_bounty_id(parent_bounty_id)
        canonical_child = validate_evm_address(child_bounty_id)
        economics = BountyEconomics(
            solver_reward_usdc=reward_usdc,
            bond_usdc=bond_usdc,
            total_funding_usdc=round(reward_usdc + bond_usdc, 4),
        )
        spec = ChildBountySpec(
            bounty_id=canonical_child,
            parent_bounty_id=parent_bounty_id,
            title=title,
            description=description,
            economics=economics,
            verifier_type=verifier_type,
            deadline_timestamp=deadline_timestamp,
        )
        self.registry.bounties[canonical_child] = spec
        self.registry.bounty_states[canonical_child] = BountyStatus.UNAVAILABLE
        self.registry.publication_timestamps[canonical_child] = timestamp
        return spec

    def fund_child_escrow(
        self,
        bounty_id: str,
        funder_address: str,
        amount_usdc: float,
        timestamp: int,
    ) -> None:
        """Deposit exact funding for child bounty escrow and transition state.

        Args:
            bounty_id: Child bounty address.
            funder_address: EVM address of parent creator depositing funds.
            amount_usdc: Escrow funding amount in USDC.
            timestamp: Block timestamp of escrow funding confirmation.

        Raises:
            ValueError: If funder is unregistered, role invalid, or amount incorrect.
        """
        canonical_bounty = validate_evm_address(bounty_id)
        canonical_funder = validate_evm_address(funder_address)

        if canonical_bounty not in self.registry.bounties:
            raise ValueError(f"Unknown bounty {canonical_bounty}")

        if canonical_funder not in self.registry.participants:
            raise ValueError(f"Funder {canonical_funder} is not registered")

        participant = self.registry.participants[canonical_funder]
        if participant.role != ParticipantRole.PARENT_CREATOR:
            raise ValueError(f"Funder role must be PARENT_CREATOR, got {participant.role}")

        spec = self.registry.bounties[canonical_bounty]
        if round(amount_usdc, 4) != round(spec.total_funding_usdc, 4):
            err_msg = (
                f"Funding amount {amount_usdc} must equal child funding {spec.total_funding_usdc}"
            )
            raise ValueError(err_msg)

        current_state = self.registry.bounty_states[canonical_bounty]
        if current_state != BountyStatus.UNAVAILABLE:
            raise ValueError(f"Bounty not in UNAVAILABLE state, current: {current_state}")

        self.registry.bounty_states[canonical_bounty] = BountyStatus.READY_TO_EARN
        self.registry.bounty_funders[canonical_bounty] = canonical_funder
        self.registry.funding_timestamps[canonical_bounty] = timestamp

    def claim_parent_bounty(
        self,
        parent_bounty_id: str,
        child_bounty_id: str,
        funder_address: str,
        bond_usdc: float,
        timestamp: int,
    ) -> None:
        """Post parent claim bond asserting valid child decomposition.

        Args:
            parent_bounty_id: Parent bounty contract address.
            child_bounty_id: Child bounty contract address.
            funder_address: EVM address of parent coordinator.
            bond_usdc: Claim bond amount deposited.
            timestamp: Block timestamp of claim transaction.

        Raises:
            ValueError: If child bounty is unfunded or timestamp ordering is violated.
        """
        validate_bounty_id(parent_bounty_id)
        canonical_child = validate_evm_address(child_bounty_id)
        canonical_funder = validate_evm_address(funder_address)

        if canonical_funder not in self.registry.participants:
            raise ValueError(f"Funder {canonical_funder} is not registered")

        if not self.registry.is_bounty_funded(canonical_child):
            raise ValueError(f"Child bounty {canonical_child} must be funded before parent claim")

        funding_ts = self.registry.get_funding_timestamp(canonical_child)
        if timestamp <= funding_ts:
            raise ValueError("Parent claim timestamp must be strictly greater than child funding")

        if bond_usdc < 0.01:
            raise ValueError(f"Parent claim bond must be at least 0.01 USDC, got {bond_usdc}")

    def claim_child_bounty(
        self,
        bounty_id: str,
        solver_address: str,
        bond_usdc: float,
        timestamp: int,
    ) -> None:
        """Claim child bounty execution slot and lock solver bond.

        Args:
            bounty_id: Child bounty address.
            solver_address: EVM address of child solver participant.
            bond_usdc: Solver entry bond deposited.
            timestamp: Block timestamp of claim.

        Raises:
            ValueError: If solver role is invalid, state is not ready, or self-dealing is attempted.
        """
        canonical_bounty = validate_evm_address(bounty_id)
        canonical_solver = validate_evm_address(solver_address)

        if canonical_bounty not in self.registry.bounties:
            raise ValueError(f"Unknown bounty {canonical_bounty}")

        if canonical_solver not in self.registry.participants:
            raise ValueError(f"Solver {canonical_solver} is not registered")

        participant = self.registry.participants[canonical_solver]
        if participant.role != ParticipantRole.CHILD_SOLVER:
            raise ValueError(f"Solver role must be CHILD_SOLVER, got {participant.role}")

        funder = self.registry.bounty_funders.get(canonical_bounty)
        if funder == canonical_solver:
            raise ValueError("Parent creator cannot claim child bounty (anti-self-dealing)")

        current_state = self.registry.bounty_states[canonical_bounty]
        if current_state != BountyStatus.READY_TO_EARN:
            raise ValueError(f"Bounty must be in READY_TO_EARN state, current: {current_state}")

        spec = self.registry.bounties[canonical_bounty]
        if round(bond_usdc, 4) < round(spec.bond_usdc, 4):
            raise ValueError(
                f"Solver bond {bond_usdc} USDC is less than required {spec.bond_usdc} USDC"
            )

        self.registry.bounty_states[canonical_bounty] = BountyStatus.EXCLUSIVE_CLAIM
        self.registry.bounty_solvers[canonical_bounty] = canonical_solver
        self.registry.claim_timestamps[canonical_bounty] = timestamp

    def record_execution(
        self,
        bounty_id: str,
        solver_address: str,
        output_payload: str,
        status_code: int,
        timestamp: int,
    ) -> ExecutionReceipt:
        """Generate execution receipt from solver API run.

        Args:
            bounty_id: Child bounty address.
            solver_address: Solving agent address.
            output_payload: Serialized test or execution response.
            status_code: Execution HTTP or process exit status code.
            timestamp: Block timestamp of execution.

        Returns:
            ExecutionReceipt record.

        Raises:
            ValueError: If bounty is not in EXCLUSIVE_CLAIM or solver does not match claimant.
        """
        canonical_bounty = validate_evm_address(bounty_id)
        canonical_solver = validate_evm_address(solver_address)

        current_state = self.registry.bounty_states.get(canonical_bounty)
        if current_state != BountyStatus.EXCLUSIVE_CLAIM:
            raise ValueError(f"Bounty not in EXCLUSIVE_CLAIM state, current: {current_state}")

        assigned_solver = self.registry.bounty_solvers.get(canonical_bounty)
        if assigned_solver != canonical_solver:
            raise ValueError(f"Solver {canonical_solver} does not hold exclusive claim")

        output_digest = compute_sha256_digest(output_payload)
        receipt_material = f"{canonical_bounty}:{canonical_solver}:{output_digest}:{timestamp}"
        receipt_id = f"0x{compute_sha256_digest(receipt_material)}"

        receipt = ExecutionReceipt(
            receipt_id=receipt_id,
            bounty_id=canonical_bounty,
            solver_address=canonical_solver,
            status_code=status_code,
            output_payload=output_payload,
            output_digest=output_digest,
            execution_timestamp=timestamp,
        )
        return receipt

    def settle_child_bounty(
        self,
        receipt: ExecutionReceipt,
        task_vector: APITaskVector,
        timestamp: int,
    ) -> tuple[QuorumVerification, CanonicalSettlementReceipt, ParentProofPayload]:
        """Evaluate verifier quorum consensus, settle child bounty, and generate parent proof.

        Args:
            receipt: Solver execution receipt.
            task_vector: Deterministic API task vector specification.
            timestamp: Settlement block timestamp.

        Returns:
            Tuple of (QuorumVerification, CanonicalSettlementReceipt, ParentProofPayload).

        Raises:
            RuntimeError: If verifier quorum consensus is not reached.
        """
        canonical_bounty = validate_evm_address(receipt.bounty_id)
        quorum = self.verifier.verify_execution(receipt, task_vector, timestamp)

        if not quorum.passed:
            sig_count = len(quorum.signatures)
            err_msg = (
                f"Quorum consensus failed: threshold {quorum.threshold} not met ({sig_count} sigs)"
            )
            raise RuntimeError(err_msg)

        self.registry.bounty_states[canonical_bounty] = BountyStatus.SETTLED
        spec = self.registry.bounties[canonical_bounty]

        tx_material = f"BountySettled:{canonical_bounty}:{receipt.solver_address}:{timestamp}"
        tx_hash = f"0x{compute_sha256_digest(tx_material)}"
        anchor = BlockAnchor(transaction_hash=tx_hash, block_number=21890456)

        proof_hex = abi_encode_address(canonical_bounty)
        settlement_receipt = CanonicalSettlementReceipt(
            event_type="BountySettled(bytes32,address,uint256,address)",
            anchor=anchor,
            timestamp=timestamp,
            bounty_id=canonical_bounty,
            solver_address=receipt.solver_address,
            payout_usdc=spec.solver_reward_usdc,
            proof_hex=proof_hex,
        )
        self.registry.settlement_receipts[canonical_bounty] = settlement_receipt

        parent_proof = ParentProofPayload(
            child_bounty_address=canonical_bounty,
            encoded_abi=proof_hex,
            discovery_feedback="API child bounty verified and canonically settled on Base",
            proof_digest=quorum.verification_digest,
        )

        result = (quorum, settlement_receipt, parent_proof)
        return result

    def calculate_economics(
        self,
        parent_reward_usdc: float = 2.00,
        child_funding_usdc: float = 1.00,
        parent_claim_bond_usdc: float = 0.01,
    ) -> EconomicMarginAnalysis:
        """Compute economic spread and retained margin between parent and child bounties.

        Args:
            parent_reward_usdc: Gross parent bounty coordination reward.
            child_funding_usdc: Outflow funding deposited into child escrow.
            parent_claim_bond_usdc: Refundable bond posted by parent coordinator.

        Returns:
            EconomicMarginAnalysis breakdown.
        """
        gross_profit = round(parent_reward_usdc - child_funding_usdc, 4)
        margin_pct = round((gross_profit / parent_reward_usdc) * 100.0, 2)

        analysis = EconomicMarginAnalysis(
            parent_reward_usdc=parent_reward_usdc,
            child_funding_usdc=child_funding_usdc,
            parent_claim_bond_usdc=parent_claim_bond_usdc,
            gross_profit_usdc=gross_profit,
            net_margin_percentage=margin_pct,
            payout_routing_evm=DEFAULT_EVM_PAYOUT,
            payout_routing_stellar=DEFAULT_STELLAR_PAYOUT,
        )
        return analysis


def main() -> int:
    """Module CLI entrypoint.

    Returns:
        Exit code.
    """
    seeder = APIBountySeeder()
    analysis = seeder.calculate_economics()
    print(f"Bounty Seeder Ready: gross margin {analysis.gross_profit_usdc:.2f} USDC")
    return 0


if __name__ == "__main__":
    sys.exit(main())
