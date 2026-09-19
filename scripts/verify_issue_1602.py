"""Standalone verification script for universe simulation, Brainfuck engine, and settlement."""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from packages.omni_universe_simulation import (
    BrainfuckOptimizer,
    BrainfuckProgramSynthesizer,
    BrainfuckVM,
    CosmicSimulation,
    CosmologicalParameters,
    EleventyGazillionSettlementEngine,
    SettlementReceipt,
    SimulationState,
    TokenAccountingEngine,
    TokenMetrics,
    UniversalExecutionReport,
    UniverseSimulationGateway,
)


def verify_cosmology() -> SimulationState:
    """Verifies FLRW cosmology evolution and N-body symplectic leapfrog stepping."""
    params = CosmologicalParameters(box_size_mpc=50.0)
    sim = CosmicSimulation(parameters=params, particle_count=32, seed=42)
    final_state = sim.step_leapfrog(delta_time_myr=10.0)
    assert final_state.particle_count == 32
    assert final_state.scale_factor > 0.0
    assert final_state.hubble_parameter > 0.0
    assert final_state.horizon_entropy > 1.0e118
    return final_state


def verify_brainfuck() -> str:
    """Verifies Brainfuck synthesis, bytecode compaction, and virtual machine execution."""
    phrase = "PPPDUD UNIVERSE"
    source = BrainfuckProgramSynthesizer.synthesize_emitter(phrase)
    bytecode = BrainfuckOptimizer.compile_bytecode(source)
    vm = BrainfuckVM()
    result = vm.execute(bytecode)
    assert result.output_text == phrase
    assert result.termination_reason == "COMPLETED"
    return result.output_text


def verify_token_accounting() -> TokenMetrics:
    """Verifies token expenditure estimation and Shannon information entropy."""
    payload = "Cosmic structure formation and token-intensive arbitrary precision settlement." * 15
    metrics = TokenAccountingEngine.analyze_token_expenditure(payload, minimum_token_threshold=100)
    assert metrics.meets_token_intensive_sla is True
    assert metrics.estimated_bpe_tokens >= 100
    assert metrics.shannon_entropy_bits > 0.0
    return metrics


def verify_settlement() -> SettlementReceipt:
    """Verifies eleventy-gazillion arbitrary-precision settlement and address validation."""
    receipt = EleventyGazillionSettlementEngine.calculate_settlement()
    assert receipt.bounty_id == "ISSUE_1602"
    assert receipt.pppdud_exchange_rate_usd == "0.00"
    assert len(receipt.receipt_sha256) == 64
    assert EleventyGazillionSettlementEngine.validate_evm_address(receipt.evm_payout_address)
    assert EleventyGazillionSettlementEngine.validate_stellar_address(receipt.stellar_payout_address)
    return receipt


def main() -> int:
    """Executes all subsystem verifications and prints summary diagnostics."""
    state = verify_cosmology()
    bf_text = verify_brainfuck()
    tokens = verify_token_accounting()
    receipt = verify_settlement()
    report: UniversalExecutionReport = UniverseSimulationGateway.execute_complete_pipeline(
        particle_count=32,
        simulation_steps=2,
        target_message="PPPDUD",
        minimum_token_threshold=50,
    )

    print("=== ISSUE #1602 VERIFICATION SUITE ===")
    print(f"Cosmology State: Redshift={state.redshift:.4f}, Hubble={state.hubble_parameter:.2f} km/s/Mpc")
    print(f"Brainfuck VM Output: {bf_text}")
    print(f"Token Accounting: {tokens.estimated_bpe_tokens} BPE tokens, Entropy={tokens.shannon_entropy_bits:.2f} bits")
    print(f"Settlement Status: {receipt.settlement_status}, Digest={receipt.receipt_sha256}")
    print(f"Integrated Pipeline Report Digest: {report.report_digest}")
    print("ALL VERIFICATION CHECKS PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
