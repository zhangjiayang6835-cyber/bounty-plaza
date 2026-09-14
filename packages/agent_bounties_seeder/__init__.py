"""Agent Bounties paid CLI child bounty seeder and canonical settlement engine."""

from packages.agent_bounties_seeder.cli import create_cli_parser, main as cli_main, run_demo
from packages.agent_bounties_seeder.models import (
    BountyStatus,
    CanonicalSettlementReceipt,
    ChildBountySpec,
    DeterministicTaskVector,
    EconomicMarginAnalysis,
    ExecutionReceipt,
    ParentProofPayload,
    Participant,
    ParticipantRole,
    QuorumVerification,
    abi_encode_address,
    compute_sha256_digest,
    validate_evm_address,
)
from packages.agent_bounties_seeder.seeder import CLIBountySeeder, main as seeder_main
from packages.agent_bounties_seeder.verifier import DeterministicModuleVerifier

__all__ = [
    "BountyStatus",
    "CLIBountySeeder",
    "CanonicalSettlementReceipt",
    "ChildBountySpec",
    "DeterministicModuleVerifier",
    "DeterministicTaskVector",
    "EconomicMarginAnalysis",
    "ExecutionReceipt",
    "ParentProofPayload",
    "Participant",
    "ParticipantRole",
    "QuorumVerification",
    "abi_encode_address",
    "cli_main",
    "compute_sha256_digest",
    "create_cli_parser",
    "run_demo",
    "seeder_main",
    "validate_evm_address",
]
