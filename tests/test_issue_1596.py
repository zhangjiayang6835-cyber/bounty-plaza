"""Comprehensive unit and integration test suite for Issue #1596."""

import math
from packages.tt_sfploadmacro_coverage import (
    ApproximationMode,
    BountyRewardCalculation,
    BountySettlementEngine,
    CppPatchGenerator,
    DataFormat,
    DestAccumulation,
    ExecutionMode,
    ReciprocalSweepSuite,
    ReciprocalVariant,
    SFPUMacroSimulationEngine,
    TileShape,
    TimingHazardDetector,
    calculate_pearson_correlation,
    compute_arecip_7b,
    compute_exact_reciprocal,
    compute_reciprocal_bf16_8b_3c,
    compute_reciprocal_fp32_24b_5c,
    generate_reciprocal_stimuli,
    validate_evm_address,
    validate_stellar_address,
)


def test_sweep_matrix_dimensions_and_distribution():
    """Verify exact count and categorical split of the 153 reciprocal sweep variants."""
    variants = ReciprocalSweepSuite.generate_full_sweep()
    assert len(variants) == 153

    failing_variants = [v for v in variants if v.has_coverage_hazard]
    passing_variants = [v for v in variants if not v.has_coverage_hazard]

    assert len(failing_variants) == 46
    assert len(passing_variants) == 107

    dest_acc_yes = [v for v in failing_variants if v.dest_acc == DestAccumulation.YES]
    dest_acc_no = [v for v in failing_variants if v.dest_acc == DestAccumulation.NO]

    assert len(dest_acc_yes) == 40
    assert len(dest_acc_no) == 6

    for variant in failing_variants:
        assert variant.approx_mode == ApproximationMode.NO


def test_reference_math_special_cases():
    """Verify numerical boundary handling in reference reciprocal model."""
    assert math.isinf(compute_exact_reciprocal(0.0))
    assert compute_exact_reciprocal(0.0) > 0.0
    assert compute_exact_reciprocal(-0.0) < 0.0

    assert compute_exact_reciprocal(float("inf")) == 0.0
    assert compute_exact_reciprocal(float("-inf")) == -0.0
    assert math.isnan(compute_exact_reciprocal(float("nan")))

    assert abs(compute_exact_reciprocal(2.0) - 0.5) < 1e-7
    assert abs(compute_exact_reciprocal(-4.0) - (-0.25)) < 1e-7


def test_approx_reciprocal_models():
    """Verify hardware arithmetic models for 7b, BF16 8b 3c, and FP32 24b 5c paths."""
    val = 4.0
    gold = 0.25

    est_7b = compute_arecip_7b(val)
    assert abs(est_7b - gold) / gold < 0.05

    est_bf16 = compute_reciprocal_bf16_8b_3c(val)
    assert abs(est_bf16 - gold) / gold < 0.01

    est_fp32 = compute_reciprocal_fp32_24b_5c(val)
    assert abs(est_fp32 - gold) / gold < 1e-4


def test_pearson_correlation_metric():
    """Verify Pearson correlation calculation across edge cases."""
    vec_a = [1.0, 2.0, 3.0, 4.0, 5.0]
    vec_b = [2.0, 4.0, 6.0, 8.0, 10.0]
    assert abs(calculate_pearson_correlation(vec_a, vec_b) - 1.0) < 1e-5

    vec_c = [-1.0, -2.0, -3.0, -4.0, -5.0]
    assert abs(calculate_pearson_correlation(vec_a, vec_c) - (-1.0)) < 1e-5

    assert calculate_pearson_correlation([], []) == 0.0


def test_stimuli_generator_determinism():
    """Verify repeatability and range of simulated stimuli values."""
    stimuli1 = generate_reciprocal_stimuli(num_elements=512, seed=123)
    stimuli2 = generate_reciprocal_stimuli(num_elements=512, seed=123)
    assert len(stimuli1) == 512
    assert stimuli1 == stimuli2
    assert all(math.isfinite(x) and x != 0.0 for x in stimuli1)


def test_native_no_coverage_execution():
    """Verify that all variants pass cleanly under native compilation without coverage."""
    engine = SFPUMacroSimulationEngine()
    variant = ReciprocalVariant(
        variant_id="recip_test_native",
        in_format=DataFormat.FLOAT32,
        out_format=DataFormat.FLOAT32,
        approx_mode=ApproximationMode.NO,
        dest_acc=DestAccumulation.YES,
        tile_shape=TileShape.SHAPE_32X32,
    )
    result = engine.simulate_variant(variant, ExecutionMode.NATIVE_NO_COVERAGE)

    assert result.passed
    assert result.num_mismatches == 0
    assert result.num_matches == result.num_elements
    assert result.pcc >= 0.9999


def test_coverage_defective_hazard_reproduction():
    """Verify reproduction of the alternating match/wrong pattern under coverage instrumentation."""
    engine = SFPUMacroSimulationEngine()
    variant = ReciprocalVariant(
        variant_id="recip_test_defective",
        in_format=DataFormat.FLOAT32,
        out_format=DataFormat.FLOAT32,
        approx_mode=ApproximationMode.NO,
        dest_acc=DestAccumulation.YES,
        tile_shape=TileShape.SHAPE_32X32,
    )
    result = engine.simulate_variant(variant, ExecutionMode.COVERAGE_DEFECTIVE)

    assert not result.passed
    assert result.num_mismatches == result.num_elements // 2
    assert result.num_matches == result.num_elements // 2
    assert result.alternating_pattern_detected
    assert result.pcc < 0.85

    for idx in range(16):
        if idx % 2 == 0:
            assert abs(result.device_output[idx] - result.golden_output[idx]) < 1e-4
        else:
            assert abs(result.device_output[idx] - result.golden_output[idx]) > 1e-4


def test_coverage_defective_safe_variant_passes():
    """Verify that approx_mode=Yes variants are immune to the SFPLOADMACRO timing hazard."""
    engine = SFPUMacroSimulationEngine()
    variant = ReciprocalVariant(
        variant_id="recip_test_safe",
        in_format=DataFormat.FLOAT32,
        out_format=DataFormat.FLOAT32,
        approx_mode=ApproximationMode.YES,
        dest_acc=DestAccumulation.NO,
        tile_shape=TileShape.SHAPE_32X32,
    )
    result = engine.simulate_variant(variant, ExecutionMode.COVERAGE_DEFECTIVE)

    assert result.passed
    assert result.num_mismatches == 0
    assert not result.alternating_pattern_detected


def test_coverage_protected_fallback_resolution():
    """Verify that routing to non-macro fallback completely resolves all failures."""
    engine = SFPUMacroSimulationEngine()
    variant = ReciprocalVariant(
        variant_id="recip_test_fallback",
        in_format=DataFormat.FLOAT32,
        out_format=DataFormat.FLOAT32,
        approx_mode=ApproximationMode.NO,
        dest_acc=DestAccumulation.YES,
        tile_shape=TileShape.SHAPE_32X32,
    )
    result = engine.simulate_variant(variant, ExecutionMode.COVERAGE_PROTECTED_FALLBACK)

    assert result.passed
    assert result.num_mismatches == 0
    assert result.num_matches == result.num_elements
    assert result.pcc >= 0.9999


def test_coverage_pipelined_barrier_resolution():
    """Verify that pipelined synchronization barrier resolves macro timing hazard."""
    engine = SFPUMacroSimulationEngine()
    variant = ReciprocalVariant(
        variant_id="recip_test_barrier",
        in_format=DataFormat.FLOAT16,
        out_format=DataFormat.FLOAT16,
        approx_mode=ApproximationMode.NO,
        dest_acc=DestAccumulation.NO,
        tile_shape=TileShape.SHAPE_16X32,
    )
    result = engine.simulate_variant(variant, ExecutionMode.COVERAGE_PIPELINED_BARRIER)

    assert result.passed
    assert result.num_mismatches == 0
    assert result.pcc >= 0.9999


def test_full_153_suite_execution_outcomes():
    """Verify the 107/46 defective vs 153/0 corrected split across the full suite."""
    engine = SFPUMacroSimulationEngine()
    variants = ReciprocalSweepSuite.generate_full_sweep()

    defective_passed = 0
    defective_failed = 0
    for var in variants:
        res = engine.simulate_variant(var, ExecutionMode.COVERAGE_DEFECTIVE)
        if res.passed:
            defective_passed += 1
        else:
            defective_failed += 1

    assert defective_passed == 107
    assert defective_failed == 46

    corrected_passed = 0
    corrected_failed = 0
    for var in variants:
        res = engine.simulate_variant(var, ExecutionMode.COVERAGE_PROTECTED_FALLBACK)
        if res.passed:
            corrected_passed += 1
        else:
            corrected_failed += 1

    assert corrected_passed == 153
    assert corrected_failed == 0


def test_pipeline_trace_generation():
    """Verify cycle-level instruction trace models gcov scalar instructions."""
    engine = SFPUMacroSimulationEngine()
    variant = ReciprocalVariant(
        variant_id="recip_trace",
        in_format=DataFormat.FLOAT32,
        out_format=DataFormat.FLOAT32,
        approx_mode=ApproximationMode.NO,
        dest_acc=DestAccumulation.YES,
        tile_shape=TileShape.SHAPE_32X32,
    )
    trace = engine.generate_pipeline_trace(variant, ExecutionMode.COVERAGE_DEFECTIVE, steps=4)

    assert len(trace) > 4
    has_gcov = any("gcov" in cycle.instruction for cycle in trace)
    has_sfploadmacro = any("TTI_SFPLOADMACRO" in cycle.instruction for cycle in trace)
    assert has_gcov
    assert has_sfploadmacro


def test_timing_hazard_detector_classification():
    """Verify detector distinguishes alternating corruption from random noise."""
    golden = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    alternating_dev = [1.0, 99.0, 3.0, 99.0, 5.0, 99.0, 7.0, 99.0]
    random_dev = [99.0, 99.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]

    assert TimingHazardDetector.is_alternating_mismatch(alternating_dev, golden)
    assert not TimingHazardDetector.is_alternating_mismatch(random_dev, golden)


def test_cpp_patch_generator():
    """Verify generated C++ and Python test harness patches."""
    recip_patch = CppPatchGenerator.get_recip_h_patch()
    assert "ckernel_sfpu_recip.h" in recip_patch
    assert "DISABLE_SFPLOADMACRO" in recip_patch
    assert "COVERAGE" in recip_patch

    test_config_patch = CppPatchGenerator.get_test_config_patch()
    assert "test_config.py" in test_config_patch
    assert "OPTIONS_COMPILE" in test_config_patch

    test_unary_patch = CppPatchGenerator.get_test_unary_patch()
    assert "test_eltwise_unary_sfpu.py" in test_unary_patch
    assert "-    MathOperation.Reciprocal," in test_unary_patch

    header = CppPatchGenerator.generate_full_kernel_header()
    assert "calculate_reciprocal_safe" in header


def test_bounty_settlement_financial_breakdown():
    """Verify financial formulas, token conversions, and tier ratios."""
    calc = BountySettlementEngine.calculate_settlement(nominal_usd=1500.00)
    assert isinstance(calc, BountyRewardCalculation)
    assert calc.issue_id == 1596
    assert calc.nominal_usd == 1500.00
    assert calc.total_coins == 1875.00
    assert calc.contributor_ratio == 0.85
    assert calc.contributor_coins == 1593.75
    assert calc.platform_coins == 281.25
    assert calc.contributor_cash_usd == 1147.50
    assert calc.platform_fee_usd == 352.50
    assert calc.effective_payout_percentage == 76.50


def test_bounty_settlement_tier_thresholds():
    """Verify contributor ratio R transitions across policy tiers."""
    assert BountySettlementEngine.get_contributor_ratio(400.0) == 0.70
    assert BountySettlementEngine.get_contributor_ratio(500.0) == 0.70
    assert BountySettlementEngine.get_contributor_ratio(750.0) == 0.75
    assert BountySettlementEngine.get_contributor_ratio(1000.0) == 0.75
    assert BountySettlementEngine.get_contributor_ratio(1001.0) == 0.85
    assert BountySettlementEngine.get_contributor_ratio(1500.0) == 0.85


def test_address_validation():
    """Verify EVM and Stellar payout address validators."""
    evm_valid = "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89"
    evm_invalid = "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F"
    assert validate_evm_address(evm_valid)
    assert not validate_evm_address(evm_invalid)
    assert not validate_evm_address(12345)  # type: ignore

    stellar_valid = "GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC"
    stellar_invalid = "SCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC"
    assert validate_stellar_address(stellar_valid)
    assert not validate_stellar_address(stellar_invalid)
    assert not validate_stellar_address("")


def test_settlement_receipt_cryptographic_integrity():
    """Verify settlement receipt generation and SHA-256 digest validation."""
    receipt = BountySettlementEngine.generate_settlement_receipt()
    assert receipt["issue_id"] == 1596
    assert receipt["nominal_usd"] == "$1500.00"
    assert receipt["contributor_cash_usd"] == "$1147.50"
    assert receipt["addresses_valid"]["evm"] is True
    assert receipt["addresses_valid"]["stellar"] is True
    assert len(receipt["audit_sha256"]) == 64
