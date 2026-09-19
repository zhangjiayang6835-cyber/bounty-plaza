"""Comprehensive test suite for the universe simulation, Brainfuck VM, and settlement engine."""

from decimal import Decimal
import pytest
from packages.omni_universe_simulation import (
    BrainfuckExecutionResult,
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


def test_cosmological_parameters_defaults() -> None:
    """Verifies that default cosmological parameters match Planck baseline values."""
    params = CosmologicalParameters()
    assert params.omega_matter == 0.315
    assert params.omega_lambda == 0.6849
    assert params.hubble_constant_h0 == 67.4
    assert params.baryon_fraction == 0.049


def test_hubble_parameter_evolution() -> None:
    """Verifies that the Hubble parameter increases monotonically with redshift."""
    sim = CosmicSimulation()
    h_z0 = sim.compute_hubble_parameter(0.0)
    h_z1 = sim.compute_hubble_parameter(1.0)
    h_z5 = sim.compute_hubble_parameter(5.0)

    assert abs(h_z0 - 67.4) < 0.1
    assert h_z1 > h_z0
    assert h_z5 > h_z1


def test_scale_factor_monotonicity() -> None:
    """Verifies the cosmological scale factor a(z) = 1 / (1 + z)."""
    sim = CosmicSimulation()
    assert abs(sim.compute_scale_factor(0.0) - 1.0) < 1.0e-5
    assert abs(sim.compute_scale_factor(1.0) - 0.5) < 1.0e-5
    assert abs(sim.compute_scale_factor(9.0) - 0.1) < 1.0e-5


def test_horizon_entropy_positivity() -> None:
    """Verifies that cosmic horizon entropy evaluates to a strictly positive magnitude."""
    sim = CosmicSimulation()
    entropy = sim.compute_horizon_entropy(0.0)
    assert entropy > 1.0e120


def test_power_spectrum_and_correlation() -> None:
    """Verifies the matter power spectrum P(k) and two-point correlation function xi(r)."""
    sim = CosmicSimulation()
    p_k = sim.compute_power_spectrum(0.1, 0.0)
    xi_5 = sim.compute_two_point_correlation(5.0)
    xi_10 = sim.compute_two_point_correlation(10.0)

    assert p_k > 0.0
    assert abs(xi_5 - 1.0) < 1.0e-2
    assert xi_10 < xi_5


def test_particle_mesh_initialization() -> None:
    """Verifies that initial particle generation populates baryonic and dark matter elements."""
    sim = CosmicSimulation(particle_count=32, seed=123)
    assert len(sim.particles) == 32

    baryon_count = sum(1 for p in sim.particles if p.species == "baryon")
    cdm_count = sum(1 for p in sim.particles if p.species == "cdm")

    assert baryon_count > 0
    assert cdm_count > 0
    assert baryon_count + cdm_count == 32

    for p in sim.particles:
        assert 0.0 <= p.position_x <= 100.0
        assert 0.0 <= p.position_y <= 100.0
        assert 0.0 <= p.position_z <= 100.0


def test_nbody_leapfrog_step() -> None:
    """Verifies that leapfrog integration advances cosmic time and updates state variables."""
    sim = CosmicSimulation(particle_count=16, seed=99)
    initial_time = sim.cosmic_time_myr
    initial_redshift = sim.redshift

    state: SimulationState = sim.step_leapfrog(delta_time_myr=5.0)

    assert state.cosmic_time_myr > initial_time
    assert state.redshift < initial_redshift
    assert state.particle_count == 16
    assert state.mean_matter_density > 0.0
    assert state.clustering_index >= 0.0


def test_brainfuck_optimizer_compaction() -> None:
    """Verifies that repeated Brainfuck characters are compacted into parameterized opcodes."""
    source = "+++++>>><<[-].."
    bytecode = BrainfuckOptimizer.compile_bytecode(source)

    op_codes = [op.op_code for op in bytecode]
    assert "ADD_VAL" in op_codes
    assert "SHIFT_PTR" in op_codes
    assert "CLEAR_CELL" in op_codes
    assert "OUTPUT_CHAR" in op_codes

    first_op = bytecode[0]
    assert first_op.op_code == "ADD_VAL"
    assert first_op.argument == 5


def test_brainfuck_loop_bracket_matching() -> None:
    """Verifies that matched brackets link jump targets bidirectionally."""
    source = "++[>+<-]"
    bytecode = BrainfuckOptimizer.compile_bytecode(source)

    loop_start_ops = [i for i, op in enumerate(bytecode) if op.op_code == "LOOP_START"]
    loop_end_ops = [i for i, op in enumerate(bytecode) if op.op_code == "LOOP_END"]

    assert len(loop_start_ops) == 1
    assert len(loop_end_ops) == 1
    assert bytecode[loop_start_ops[0]].argument == loop_end_ops[0]
    assert bytecode[loop_end_ops[0]].argument == loop_start_ops[0]


def test_brainfuck_unmatched_brackets() -> None:
    """Verifies that syntax errors with unbalanced brackets raise ValueError."""
    with pytest.raises(ValueError):
        BrainfuckOptimizer.compile_bytecode("[[+]")
    with pytest.raises(ValueError):
        BrainfuckOptimizer.compile_bytecode("++]-")


def test_brainfuck_vm_execution() -> None:
    """Verifies virtual machine tape mutations, cell wrapping, and standard output."""
    source = "++++++++[>++++[>++>+++>+++>+<<<<-]>+>+>->>+[<]<-]>>.>---.+++++++..+++.>>.<-.<.+++.------.--------.>>+.>++."
    bytecode = BrainfuckOptimizer.compile_bytecode(source)
    vm = BrainfuckVM()
    result: BrainfuckExecutionResult = vm.execute(bytecode)

    assert result.output_text == "Hello World!\n"
    assert result.cycles_executed > 0
    assert result.cells_used > 0
    assert result.termination_reason == "COMPLETED"


def test_brainfuck_synthesizer_and_execution() -> None:
    """Verifies automated Brainfuck synthesis for target token strings."""
    target = "PPPDUD"
    synthesized_code = BrainfuckProgramSynthesizer.synthesize_emitter(target)
    assert len(synthesized_code) > 0

    bytecode = BrainfuckOptimizer.compile_bytecode(synthesized_code)
    vm = BrainfuckVM()
    result = vm.execute(bytecode)

    assert result.output_text == target
    assert result.termination_reason == "COMPLETED"


def test_brainfuck_cycle_limit() -> None:
    """Verifies that infinite loops are safely halted by the instruction cycle meter."""
    infinite_loop = "+[]"
    bytecode = BrainfuckOptimizer.compile_bytecode(infinite_loop)
    vm = BrainfuckVM(cycle_limit=100)
    result = vm.execute(bytecode)

    assert result.cycles_executed == 100
    assert result.termination_reason == "CYCLE_LIMIT_EXCEEDED"


def test_token_accounting_shannon_entropy() -> None:
    """Verifies that entropy is zero for uniform strings and positive for structured text."""
    zero_entropy = TokenAccountingEngine.compute_shannon_entropy("AAAAAA")
    assert zero_entropy == 0.0

    high_entropy = TokenAccountingEngine.compute_shannon_entropy("abcdefghijklmnopqrstuvwxyz0123456789")
    assert high_entropy > 4.5


def test_token_accounting_bpe_tokens() -> None:
    """Verifies BPE token estimation across prose and programmatic constructs."""
    text = "The quick brown fox jumps over the lazy dog."
    token_count = TokenAccountingEngine.estimate_bpe_tokens(text)
    assert token_count >= 8


def test_token_accounting_expenditure_analysis() -> None:
    """Verifies token expenditure metrics, density, and SLA threshold compliance."""
    sample_text = (
        "Cosmological FLRW expansion simulation in 3D Euclidean spatial coordinates. "
        "Baryonic acoustic oscillations and cold dark matter perturbation dynamics. "
    ) * 20
    metrics: TokenMetrics = TokenAccountingEngine.analyze_token_expenditure(sample_text, minimum_token_threshold=100)

    assert metrics.character_count > 1000
    assert metrics.byte_count > 1000
    assert metrics.estimated_bpe_tokens >= 100
    assert metrics.token_to_byte_density > 0.0
    assert metrics.shannon_entropy_bits > 3.0
    assert metrics.token_waste_index > 0.0
    assert metrics.meets_token_intensive_sla is True


def test_settlement_evm_address_validation() -> None:
    """Verifies validation of EVM hexadecimal addresses."""
    valid_evm = "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89"
    invalid_short = "0xF46C9F"
    invalid_chars = "0xZZZZ9F6d70C50BF81ef3588AB523a90a594a2F89"

    assert EleventyGazillionSettlementEngine.validate_evm_address(valid_evm) is True
    assert EleventyGazillionSettlementEngine.validate_evm_address(invalid_short) is False
    assert EleventyGazillionSettlementEngine.validate_evm_address(invalid_chars) is False


def test_settlement_stellar_address_validation() -> None:
    """Verifies validation of 56-character Stellar Base32 public keys."""
    valid_stellar = "GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC"
    invalid_prefix = "BCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC"
    invalid_length = "GCL6OX"

    assert EleventyGazillionSettlementEngine.validate_stellar_address(valid_stellar) is True
    assert EleventyGazillionSettlementEngine.validate_stellar_address(invalid_prefix) is False
    assert EleventyGazillionSettlementEngine.validate_stellar_address(invalid_length) is False


def test_settlement_eleventy_gazillion_math() -> None:
    """Verifies multi-currency arbitrary-precision calculations on 10^37 magnitude figures."""
    receipt: SettlementReceipt = EleventyGazillionSettlementEngine.calculate_settlement()

    nominal_dec = Decimal(receipt.nominal_reward_usd)
    coin_dec = Decimal(receipt.coin_reward)
    contributor_coins_dec = Decimal(receipt.contributor_coins)
    contributor_cash_dec = Decimal(receipt.contributor_cash_usd)
    platform_fee_dec = Decimal(receipt.platform_fee_usd)

    assert coin_dec == nominal_dec * Decimal("1.25")
    assert contributor_coins_dec == coin_dec * Decimal("0.85")
    assert contributor_cash_dec == contributor_coins_dec * Decimal("0.72")
    assert (contributor_cash_dec + platform_fee_dec) == nominal_dec
    assert receipt.receipt_sha256 is not None
    assert len(receipt.receipt_sha256) == 64


def test_settlement_zero_rate_pppdud() -> None:
    """Verifies that 1 PPPDUD dollar strictly equals 0.00 USD."""
    receipt = EleventyGazillionSettlementEngine.calculate_settlement()
    assert receipt.pppdud_exchange_rate_usd == "0.00"


def test_settlement_sha256_receipt() -> None:
    """Verifies deterministic receipt digest reproducibility."""
    receipt_a = EleventyGazillionSettlementEngine.calculate_settlement()
    receipt_b = EleventyGazillionSettlementEngine.calculate_settlement()
    assert receipt_a.receipt_sha256 == receipt_b.receipt_sha256


def test_universe_gateway_pipeline() -> None:
    """Verifies end-to-end orchestration of cosmology, Brainfuck, tokens, and settlement."""
    report: UniversalExecutionReport = UniverseSimulationGateway.execute_complete_pipeline(
        particle_count=32,
        simulation_steps=3,
        target_message="UNIVERSE",
        minimum_token_threshold=50,
    )

    assert report.simulation_state.particle_count == 32
    assert report.brainfuck_result.output_text == "UNIVERSE"
    assert report.token_metrics.estimated_bpe_tokens >= 50
    assert report.token_metrics.meets_token_intensive_sla is True
    assert report.settlement_receipt.bounty_id == "ISSUE_1602"
    assert len(report.report_digest) == 64


def test_cosmic_clustering_evolution() -> None:
    """Verifies that multi-step time evolution updates cosmology state monotonically."""
    sim = CosmicSimulation(particle_count=16, seed=42)
    state1 = sim.step_leapfrog(5.0)
    state2 = sim.step_leapfrog(5.0)

    assert state2.cosmic_time_myr > state1.cosmic_time_myr
    assert state2.redshift < state1.redshift


def test_brainfuck_tape_bounds() -> None:
    """Verifies that pointer shift operations wrap correctly across tape boundaries."""
    source = "<+"
    bytecode = BrainfuckOptimizer.compile_bytecode(source)
    vm = BrainfuckVM(tape_size=10)
    result = vm.execute(bytecode)

    assert vm.tape[9] == 1
    assert result.termination_reason == "COMPLETED"


def test_settlement_invalid_address_exceptions() -> None:
    """Verifies that invalid payout addresses raise ValueError."""
    with pytest.raises(ValueError):
        EleventyGazillionSettlementEngine.calculate_settlement(evm_address="0x123")
    with pytest.raises(ValueError):
        EleventyGazillionSettlementEngine.calculate_settlement(stellar_address="G123")
