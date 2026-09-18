"""Autonomous coordination and lifecycle seeder for paid MCP child bounties."""

from typing import Optional
from packages.agent_bounties_mcp_seeder.models import (
    BlockAnchor,
    BountyEconomics,
    BountyStatus,
    CanonicalSettlementReceipt,
    ChildMcpBountySpec,
    DeterministicMcpTaskVector,
    EconomicMarginAnalysis,
    McpExecutionReceipt,
    McpResponseTelemetry,
    ParentProofPayload,
    Participant,
    ParticipantRole,
    abi_encode_address,
    compute_sha256_digest,
    validate_evm_address,
)
from packages.agent_bounties_mcp_seeder.verifier import DeterministicMcpModuleVerifier

DEFAULT_EVM_PAYOUT = "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89"
DEFAULT_STELLAR_PAYOUT = "GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC"


class McpBountyRegistry:
    """Internal memory storage for participants, specs, and state machines."""

    def __init__(self) -> None:
        """Initialize empty registries."""
        self.participants: dict[str, Participant] = {}
        self.bounties: dict[str, ChildMcpBountySpec] = {}
        self.bounty_states: dict[str, BountyStatus] = {}
        self.bounty_funders: dict[str, str] = {}
        self.bounty_solvers: dict[str, str] = {}
        self.timestamps: dict[str, dict[str, int]] = {}
        self.settlement_receipts: dict[str, CanonicalSettlementReceipt] = {}

    def get_terms_timestamp(self, bounty_id: str) -> int:
        """Return recorded terms timestamp for bounty."""
        return self.timestamps.get(bounty_id, {}).get("terms", 0)

    def set_terms_timestamp(self, bounty_id: str, timestamp: int) -> None:
        """Store terms timestamp for bounty."""
        if bounty_id not in self.timestamps:
            self.timestamps[bounty_id] = {}
        self.timestamps[bounty_id]["terms"] = timestamp

    def get_funding_timestamp(self, bounty_id: str) -> int:
        """Return recorded funding timestamp for bounty."""
        return self.timestamps.get(bounty_id, {}).get("funding", 0)

    def set_funding_timestamp(self, bounty_id: str, timestamp: int) -> None:
        """Store funding timestamp for bounty."""
        if bounty_id not in self.timestamps:
            self.timestamps[bounty_id] = {}
        self.timestamps[bounty_id]["funding"] = timestamp


class McpBountySeeder:
    """Coordinates lifecycle, escrow funding, and canonical settlement for MCP tasks."""

    def __init__(self, verifier: Optional[DeterministicMcpModuleVerifier] = None) -> None:
        """Initialize seeder with participant registry and state tracking."""
        self.registry = McpBountyRegistry()
        if verifier is None:
            default_nodes = (
                "0x380c1af742593dd88b6f20387e9ee693a0536731",
                "0x1518ccd19002ca3b69dc33aa4ade349f70be6446",
            )
            self.verifier = DeterministicMcpModuleVerifier(default_nodes)
        else:
            self.verifier = verifier

    @property
    def participants(self) -> dict[str, Participant]:
        """Return registered participants."""
        return self.registry.participants

    @property
    def bounties(self) -> dict[str, ChildMcpBountySpec]:
        """Return registered child bounty specifications."""
        return self.registry.bounties

    @property
    def bounty_states(self) -> dict[str, BountyStatus]:
        """Return current status of tracked bounties."""
        return self.registry.bounty_states

    def register_participant(
        self,
        address: str,
        role: ParticipantRole,
        timestamp: int,
    ) -> Participant:
        """Register a solver, creator, or verifier on Base network.

        Args:
            address: EVM hexadecimal address.
            role: Participant role enum.
            timestamp: Base block timestamp of registration.

        Returns:
            Registered Participant instance.

        Raises:
            ValueError: If address is already registered under conflicting role.
        """
        canonical_addr = validate_evm_address(address)
        if canonical_addr in self.registry.participants:
            existing = self.registry.participants[canonical_addr]
            if existing.role != role:
                raise ValueError(
                    f"Address {canonical_addr} already registered with role {existing.role}"
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
        reward_tuple: tuple[float, float] = (0.90, 0.10),
        timestamp: int = 100,
    ) -> ChildMcpBountySpec:
        """Publish exact parent-bound child terms for MCP task.

        Args:
            parent_bounty_id: Identifier of parent coordination bounty.
            title: Title of MCP coding bounty.
            description: Concrete functional requirements.
            reward_tuple: Tuple of (solver_reward_usdc, bond_usdc).
            timestamp: Base block timestamp of publication.

        Returns:
            ChildMcpBountySpec specifying child parameters.
        """
        solver_reward_usdc, bond_usdc = reward_tuple
        total_funding_usdc = round(solver_reward_usdc + bond_usdc, 4)
        economics = BountyEconomics(
            solver_reward_usdc=solver_reward_usdc,
            bond_usdc=bond_usdc,
            total_funding_usdc=total_funding_usdc,
        )

        canonical_parent = validate_evm_address(parent_bounty_id)
        seed = f"{canonical_parent}:{title}:{timestamp}"
        digest = compute_sha256_digest(seed)
        child_bounty_id = f"0x{digest[:40]}"

        spec = ChildMcpBountySpec(
            bounty_id=child_bounty_id,
            parent_bounty_id=canonical_parent,
            title=title,
            description=description,
            economics=economics,
            verifier_type="deterministic_module",
            deadline_timestamp=timestamp + 86400 * 30,
        )

        self.registry.bounties[child_bounty_id] = spec
        self.registry.bounty_states[child_bounty_id] = BountyStatus.UNAVAILABLE
        self.registry.set_terms_timestamp(child_bounty_id, timestamp)
        return spec

    def fund_child_escrow(
        self,
        child_bounty_id: str,
        funder_address: str,
        amount_usdc: float = 1.00,
        timestamp: int = 110,
    ) -> BountyStatus:
        """Fund child bounty escrow with required USDC balance.

        Args:
            child_bounty_id: Identifier of child bounty.
            funder_address: EVM address of parent creator funding child.
            amount_usdc: Amount of USDC to deposit.
            timestamp: Base block timestamp of funding.

        Returns:
            Updated BountyStatus.

        Raises:
            ValueError: If funder is not registered creator or funding amount is incorrect.
        """
        canonical_bounty = validate_evm_address(child_bounty_id)
        if canonical_bounty not in self.registry.bounties:
            raise ValueError(f"Child bounty {child_bounty_id} does not exist")

        canonical_funder = validate_evm_address(funder_address)
        if canonical_funder not in self.registry.participants:
            raise ValueError(f"Funder address {canonical_funder} must be registered")

        participant = self.registry.participants[canonical_funder]
        if participant.role != ParticipantRole.PARENT_CREATOR:
            raise ValueError("Only registered parent creator can fund child escrow")

        spec = self.registry.bounties[canonical_bounty]
        if round(amount_usdc, 4) != round(spec.total_funding_usdc, 4):
            err_msg = (
                f"Funding amount {amount_usdc} must equal child funding {spec.total_funding_usdc}"
            )
            raise ValueError(err_msg)

        terms_time = self.registry.get_terms_timestamp(canonical_bounty)
        if timestamp <= terms_time:
            raise ValueError("Child escrow funding must occur after terms publication")

        self.registry.bounty_states[canonical_bounty] = BountyStatus.READY_TO_EARN
        self.registry.bounty_funders[canonical_bounty] = canonical_funder
        self.registry.set_funding_timestamp(canonical_bounty, timestamp)
        return BountyStatus.READY_TO_EARN

    def claim_parent_bounty(
        self,
        parent_bounty_id: str,
        child_bounty_id: str,
        creator_address: str,
        bond_usdc: float = 0.01,
        timestamp: int = 120,
    ) -> bool:
        """Claim parent coordination bounty depositing refundable bond.

        Args:
            parent_bounty_id: Address of parent bounty contract.
            child_bounty_id: Address of bound child bounty contract.
            creator_address: EVM address of registered parent creator.
            bond_usdc: Refundable bond deposited on Base network.
            timestamp: Base block timestamp of claim.

        Returns:
            True if parent claim is locked and confirmed.

        Raises:
            ValueError: If validation checks fail.
        """
        validate_evm_address(parent_bounty_id)
        canonical_child = validate_evm_address(child_bounty_id)
        canonical_creator = validate_evm_address(creator_address)

        if canonical_child not in self.registry.bounties:
            raise ValueError("Bound child bounty does not exist")

        if canonical_creator not in self.registry.participants:
            raise ValueError("Creator address must be registered")

        if bond_usdc < 0.01:
            raise ValueError("Parent claim bond must be at least 0.01 USDC")

        funding_time = self.registry.get_funding_timestamp(canonical_child)
        if timestamp < funding_time:
            raise ValueError("Parent claim must not precede child funding")

        return True

    def claim_child_bounty(
        self,
        child_bounty_id: str,
        solver_address: str,
        bond_usdc: float = 0.10,
        timestamp: int = 130,
    ) -> BountyStatus:
        """Lock child bounty under exclusive claim by independent solver.

        Args:
            child_bounty_id: Identifier of child bounty.
            solver_address: Registered solver EVM address.
            bond_usdc: Solver entry/claim bond amount.
            timestamp: Base block timestamp of claim.

        Returns:
            Updated BountyStatus.

        Raises:
            ValueError: If participant is ineligible or self-dealing is detected.
        """
        canonical_bounty = validate_evm_address(child_bounty_id)
        if canonical_bounty not in self.registry.bounties:
            raise ValueError(f"Child bounty {child_bounty_id} does not exist")

        current_state = self.registry.bounty_states.get(canonical_bounty)
        if current_state != BountyStatus.READY_TO_EARN:
            raise ValueError(f"Bounty not ready to claim, current status: {current_state}")

        canonical_solver = validate_evm_address(solver_address)
        if canonical_solver not in self.registry.participants:
            raise ValueError(f"Solver address {canonical_solver} must be registered")

        participant = self.registry.participants[canonical_solver]
        if participant.role != ParticipantRole.CHILD_SOLVER:
            raise ValueError("Only registered child solver can claim child bounty")

        funder = self.registry.bounty_funders.get(canonical_bounty)
        if canonical_solver == funder:
            raise ValueError(
                "Anti-self-dealing: solver address cannot be identical to bounty funder"
            )

        spec = self.registry.bounties[canonical_bounty]
        if round(bond_usdc, 4) < round(spec.bond_usdc, 4):
            raise ValueError(f"Claim bond {bond_usdc} is below required bond {spec.bond_usdc}")

        funding_time = self.registry.get_funding_timestamp(canonical_bounty)
        if timestamp < funding_time:
            raise ValueError("Child claim timestamp cannot precede child funding")

        self.registry.bounty_states[canonical_bounty] = BountyStatus.EXCLUSIVE_CLAIM
        self.registry.bounty_solvers[canonical_bounty] = canonical_solver
        return BountyStatus.EXCLUSIVE_CLAIM

    def record_mcp_execution(
        self,
        child_bounty_id: str,
        solver_address: str,
        telemetry: McpResponseTelemetry,
        timestamp: int = 140,
    ) -> McpExecutionReceipt:
        """Record and validate solver execution of MCP task.

        Args:
            child_bounty_id: Identifier of child bounty.
            solver_address: Claimed solver EVM address.
            telemetry: Telemetry of executed MCP invocation.
            timestamp: Block timestamp of execution.

        Returns:
            Generated McpExecutionReceipt.

        Raises:
            ValueError: If bounty is not in exclusive claim state or solver does not match.
        """
        canonical_bounty = validate_evm_address(child_bounty_id)
        current_state = self.registry.bounty_states.get(canonical_bounty)
        if current_state != BountyStatus.EXCLUSIVE_CLAIM:
            raise ValueError("Bounty must be in exclusive claim state to record execution")

        canonical_solver = validate_evm_address(solver_address)
        active_solver = self.registry.bounty_solvers.get(canonical_bounty)
        if canonical_solver != active_solver:
            raise ValueError("Solver recording execution does not match claiming solver")

        receipt_seed = (
            f"{canonical_bounty}:{canonical_solver}:{telemetry.response_digest}:{timestamp}"
        )
        receipt_id = compute_sha256_digest(receipt_seed)

        receipt = McpExecutionReceipt(
            receipt_id=receipt_id,
            bounty_id=canonical_bounty,
            solver_address=canonical_solver,
            telemetry=telemetry,
            execution_timestamp=timestamp,
        )
        return receipt

    def _create_settlement_receipt(
        self,
        child_bounty_id: str,
        solver_address: str,
        payout_usdc: float,
        encoded_abi: str,
        timestamp: int,
    ) -> CanonicalSettlementReceipt:
        """Create canonical settlement event receipt."""
        tx_seed = f"tx:settle:{child_bounty_id}:{solver_address}:{timestamp}"
        tx_hash = f"0x{compute_sha256_digest(tx_seed)}"
        anchor = BlockAnchor(transaction_hash=tx_hash, block_number=21890123)

        return CanonicalSettlementReceipt(
            event_type="BountySettled",
            anchor=anchor,
            timestamp=timestamp,
            bounty_id=child_bounty_id,
            solver_address=solver_address,
            payout_usdc=payout_usdc,
            proof_hex=encoded_abi,
        )

    def _create_parent_proof(
        self,
        child_bounty_id: str,
        solver_address: str,
        encoded_abi: str,
    ) -> ParentProofPayload:
        """Create parent bounty proof payload."""
        feedback = f"mcp_child_settled:{child_bounty_id}:solver:{solver_address}"
        proof_digest = compute_sha256_digest(f"{encoded_abi}:{feedback}")

        return ParentProofPayload(
            child_bounty_address=child_bounty_id,
            encoded_abi=encoded_abi,
            discovery_feedback=feedback,
            proof_digest=proof_digest,
        )

    def verify_and_settle(
        self,
        child_bounty_id: str,
        receipt: McpExecutionReceipt,
        task_vector: DeterministicMcpTaskVector,
        timestamp: int = 150,
    ) -> tuple[CanonicalSettlementReceipt, ParentProofPayload, EconomicMarginAnalysis]:
        """Perform quorum consensus verification and issue canonical settlement receipts.

        Args:
            child_bounty_id: Identifier of child bounty.
            receipt: Solver MCP execution receipt.
            task_vector: Target deterministic MCP task specification.
            timestamp: Base block timestamp of settlement.

        Returns:
            Tuple of settlement receipt, parent proof payload, and margin analysis.

        Raises:
            RuntimeError: If quorum verification fails consensus.
            ValueError: If child bounty state is invalid.
        """
        canonical_bounty = validate_evm_address(child_bounty_id)
        current_state = self.registry.bounty_states.get(canonical_bounty)
        if current_state != BountyStatus.EXCLUSIVE_CLAIM:
            raise ValueError("Bounty must be in exclusive claim state to settle")

        verification = self.verifier.verify_execution(receipt, task_vector, timestamp)
        if not verification.passed:
            raise RuntimeError("Consensus verifier quorum rejected execution receipt")

        spec = self.registry.bounties[canonical_bounty]
        encoded_abi = abi_encode_address(canonical_bounty)

        settlement_receipt = self._create_settlement_receipt(
            canonical_bounty,
            receipt.solver_address,
            spec.solver_reward_usdc,
            encoded_abi,
            timestamp
        )
        proof_payload = self._create_parent_proof(
            canonical_bounty, receipt.solver_address, encoded_abi
        )
        margin_analysis = self.analyze_economic_margins(
            parent_reward=2.00,
            child_funding=spec.total_funding_usdc,
            claim_bond=0.01,
        )

        self.registry.bounty_states[canonical_bounty] = BountyStatus.SETTLED
        self.registry.settlement_receipts[canonical_bounty] = settlement_receipt

        return settlement_receipt, proof_payload, margin_analysis

    def analyze_economic_margins(
        self,
        parent_reward: float = 2.00,
        child_funding: float = 1.00,
        claim_bond: float = 0.01,
    ) -> EconomicMarginAnalysis:
        """Compute economic arbitrage margins for parent-child bounty pairing.

        Args:
            parent_reward: Gross reward paid by parent bounty contract in USDC.
            child_funding: Total funding allocated to child bounty escrow in USDC.
            claim_bond: Refundable parent claim bond in USDC.

        Returns:
            EconomicMarginAnalysis instance.
        """
        gross_profit = round(parent_reward - child_funding, 4)
        margin_pct = round((gross_profit / parent_reward) * 100.0, 2)

        analysis = EconomicMarginAnalysis(
            parent_reward_usdc=parent_reward,
            child_funding_usdc=child_funding,
            parent_claim_bond_usdc=claim_bond,
            gross_profit_usdc=gross_profit,
            net_margin_percentage=margin_pct,
            payout_routing_evm=DEFAULT_EVM_PAYOUT,
            payout_routing_stellar=DEFAULT_STELLAR_PAYOUT,
        )
        return analysis
