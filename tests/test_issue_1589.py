"""Comprehensive unit and integration test suite for Issue #1589."""

import pytest
from packages.tt_distributed_norm import (
    BountySettlementEngine,
    CoreGrid2D,
    CppPatchGenerator,
    LayerNormType,
    ReferenceNormEngine,
    TensorShape,
    analyze_traversal_accuracy,
    build_kernel_stride_config,
    calculate_pearson_correlation,
    compute_core_base_offset,
    compute_reference_layernorm_row,
    compute_reference_rmsnorm_row,
    compute_stats_offset,
    derive_2d_core_grid,
    generate_structured_matrix,
    simulate_reader_traversal,
    validate_evm_address,
    validate_stellar_address,
    verify_grid_coverage,
)


def test_shape_and_core_grid_derivation_single_row():
    """Verify core grid derivation for single-row tiles per core configuration."""
    shape = TensorShape(batch=1, channels=1, height=128, width=8192)
    assert shape.num_tile_rows == 4
    assert shape.num_tile_cols == 256

    grid = derive_2d_core_grid(shape, grid_size_x=8, grid_size_y=8)
    assert grid.cores_x == 4
    assert grid.cores_y == 8
    assert grid.tiles_per_core_x == 1
    assert grid.tiles_per_core_y == 32
    assert not grid.is_multi_row_per_core


def test_shape_and_core_grid_derivation_multi_row():
    """Verify core grid derivation for multi-row tiles per core configuration."""
    shape = TensorShape(batch=1, channels=1, height=512, width=4096)
    assert shape.num_tile_rows == 16
    assert shape.num_tile_cols == 128

    grid = derive_2d_core_grid(shape, grid_size_x=8, grid_size_y=8)
    assert grid.cores_x == 8
    assert grid.cores_y == 8
    assert grid.tiles_per_core_x == 2
    assert grid.tiles_per_core_y == 16
    assert grid.is_multi_row_per_core


def test_defective_reader_stride_corruption_reproduction():
    """Verify that defective reader traversal corrupts tile sequence on multi-row shapes."""
    shape = TensorShape(batch=1, channels=1, height=512, width=4096)
    grid = derive_2d_core_grid(shape)
    plan_c0 = simulate_reader_traversal(0, 0, grid, shape, defective=True)
    analysis_c0 = analyze_traversal_accuracy(plan_c0, shape)

    assert not analysis_c0["is_accurate"]
    assert analysis_c0["mismatches_count"] > 0
    assert analysis_c0["first_corrupted_step"] == grid.tiles_per_core_y

    plan_c1 = simulate_reader_traversal(1, 0, grid, shape, defective=True)
    analysis_c1 = analyze_traversal_accuracy(plan_c1, shape)
    assert not analysis_c1["is_accurate"]
    assert analysis_c1["first_corrupted_step"] == 0


def test_corrected_reader_stride_exactness():
    """Verify that corrected reader traversal matches ground truth DRAM tile IDs."""
    shape = TensorShape(batch=1, channels=1, height=512, width=4096)
    grid = derive_2d_core_grid(shape)
    plan = simulate_reader_traversal(1, 0, grid, shape, defective=False)
    analysis = analyze_traversal_accuracy(plan, shape)

    assert analysis["is_accurate"]
    assert analysis["mismatches_count"] == 0
    assert analysis["first_corrupted_step"] == -1


def test_single_row_legacy_equivalence():
    """Demonstrate why single-row shape masked corruption in earlier tests."""
    shape = TensorShape(batch=1, channels=1, height=128, width=8192)
    grid = derive_2d_core_grid(shape)
    defective_plan = simulate_reader_traversal(1, 0, grid, shape, defective=True)
    corrected_plan = simulate_reader_traversal(1, 0, grid, shape, defective=False)

    assert defective_plan.tile_indices == corrected_plan.tile_indices


def test_pre_allgather_stride_jump_formula():
    """Validate calculation of row stride jump for pre-allgather reader kernel."""
    shape = TensorShape(batch=1, channels=1, height=512, width=4096)
    grid = derive_2d_core_grid(shape)
    config = build_kernel_stride_config(0, 0, grid, shape, defective=False)

    expected_stride = shape.num_tile_cols - grid.tiles_per_core_y
    assert config.global_row_stride == expected_stride
    assert config.global_row_stride == 112


def test_post_allgather_shared_reader_stride_jump():
    """Validate shared post-allgather reader stride configuration."""
    shape = TensorShape(batch=1, channels=1, height=1024, width=2048)
    grid = derive_2d_core_grid(shape)
    config = build_kernel_stride_config(2, 3, grid, shape, stats_cols=2, defective=False)

    assert config.ncht == grid.tiles_per_core_x
    assert config.wt == grid.tiles_per_core_y
    assert config.global_row_stride == shape.num_tile_cols - grid.tiles_per_core_y
    assert config.stats_tiles_cols == 2


def test_core_base_tile_offset_calculation():
    """Verify tile base offset arithmetic for defective versus corrected models."""
    shape = TensorShape(batch=1, channels=1, height=512, width=4096)
    grid = derive_2d_core_grid(shape)
    wt_full = shape.num_tile_cols

    defective_offset = compute_core_base_offset(2, 3, grid, wt_full, defective=True)
    corrected_offset = compute_core_base_offset(2, 3, grid, wt_full, defective=False)

    assert defective_offset == (2 * wt_full) + (3 * grid.tiles_per_core_y)
    assert corrected_offset == (2 * grid.tiles_per_core_x * wt_full) + (3 * grid.tiles_per_core_y)
    assert corrected_offset > defective_offset


def test_stats_tile_offset_calculation():
    """Verify statistics tile offset calculations."""
    grid = CoreGrid2D(
        grid_size_x=8,
        grid_size_y=8,
        cores_x=8,
        cores_y=8,
        tiles_per_core_x=4,
        tiles_per_core_y=16,
    )
    defective_stats = compute_stats_offset(3, grid, stats_cols=1, defective=True)
    corrected_stats = compute_stats_offset(3, grid, stats_cols=1, defective=False)

    assert defective_stats == 3
    assert corrected_stats == 12


def test_full_grid_coverage_corrected_versus_defective():
    """Verify mesh coverage integrity across all DRAM tiles."""
    shape = TensorShape(batch=1, channels=1, height=512, width=2048)
    grid = derive_2d_core_grid(shape)

    corrected_coverage = verify_grid_coverage(shape, grid, defective=False)
    assert corrected_coverage["is_valid"]
    assert corrected_coverage["unvisited_count"] == 0
    assert corrected_coverage["duplicate_count"] == 0

    defective_coverage = verify_grid_coverage(shape, grid, defective=True)
    assert not defective_coverage["is_valid"]
    assert defective_coverage["unvisited_count"] > 0


def test_reference_rmsnorm_numerical_parity():
    """Verify reference RMSNorm row computation matches analytical values."""
    row = [2.0, -2.0, 2.0, -2.0]
    normalized = compute_reference_rmsnorm_row(row, eps=0.0)
    for val in normalized:
        assert pytest.approx(abs(val), 1e-5) == 1.0


def test_reference_layernorm_numerical_parity():
    """Verify reference LayerNorm row computation with affine parameters."""
    row = [10.0, 20.0, 30.0]
    gamma = [1.0, 2.0, 3.0]
    beta = [0.1, 0.2, 0.3]
    normalized = compute_reference_layernorm_row(row, gamma=gamma, beta=beta, eps=1e-5)

    assert len(normalized) == 3
    assert pytest.approx(normalized[0], 1e-4) == (-1.22474 * 1.0) + 0.1
    assert pytest.approx(normalized[1], 1e-4) == (0.0 * 2.0) + 0.2
    assert pytest.approx(normalized[2], 1e-4) == (1.22474 * 3.0) + 0.3


def test_pearson_correlation_metric():
    """Verify Pearson correlation calculation boundary conditions."""
    vec_a = [1.0, 2.0, 3.0, 4.0, 5.0]
    vec_b = [2.0, 4.0, 6.0, 8.0, 10.0]
    vec_c = [-1.0, -2.0, -3.0, -4.0, -5.0]

    assert pytest.approx(calculate_pearson_correlation(vec_a, vec_b), 1e-6) == 1.0
    assert pytest.approx(calculate_pearson_correlation(vec_a, vec_c), 1e-6) == -1.0


def test_hardware_simulation_pcc_corrected_multi_row():
    """Verify that corrected stride traversal yields high PCC on multi-row tensor."""
    shape = TensorShape(batch=1, channels=1, height=512, width=1024)
    matrix = generate_structured_matrix(shape)
    engine = ReferenceNormEngine(shape, norm_type=LayerNormType.RMSNORM)

    _, pcc = engine.simulate_hardware_execution(matrix, defective=False)
    assert pcc >= 0.9999


def test_hardware_simulation_pcc_defective_divergence():
    """Verify that defective stride traversal produces measurable divergence."""
    shape = TensorShape(batch=1, channels=1, height=512, width=1024)
    matrix = generate_structured_matrix(shape)
    engine = ReferenceNormEngine(shape, norm_type=LayerNormType.RMSNORM)

    _, pcc = engine.simulate_hardware_execution(matrix, defective=True)
    assert pcc < 0.90


def test_cpp_patch_generator_preallgather():
    """Verify C++ kernel generator produces valid pre-allgather source with stride jump."""
    source = CppPatchGenerator.get_preallgather_reader_source()
    analysis = CppPatchGenerator.verify_patch_invariants(source)

    assert analysis["is_valid"]
    assert analysis["has_stride_jump"]
    assert analysis["has_async_barrier"]
    assert analysis["has_arg_row_stride"]


def test_cpp_patch_generator_postallgather():
    """Verify C++ kernel generator produces valid post-allgather source with stride jump."""
    source = CppPatchGenerator.get_postallgather_reader_source()
    analysis = CppPatchGenerator.verify_patch_invariants(source)

    assert analysis["is_valid"]
    assert analysis["has_stride_jump"]
    assert analysis["has_async_barrier"]


def test_bounty_settlement_financial_breakdown():
    """Verify exact financial settlement math for 3000 USD bounty."""
    engine = BountySettlementEngine(nominal_usd="3000.00")
    result = engine.compute_settlement(
        evm_recipient="0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89",
        stellar_recipient="GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC",
        issue_id=1589,
    )

    assert result["is_valid"]
    assert result["nominal_usd"] == "3000.00"
    assert result["coins_total"] == "3750.00"
    assert result["contributor_ratio"] == "0.85"
    assert result["contributor_coins"] == "3187.50"
    assert result["platform_coins"] == "562.50"
    assert result["contributor_cash_usd"] == "2295.00"
    assert result["platform_fee_usd"] == "705.00"


def test_cryptographic_payout_address_validation():
    """Verify EVM and Stellar cryptographic address validation rules."""
    valid_evm = "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89"
    valid_stellar = "GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC"
    invalid_evm = "0x1234"
    invalid_stellar = "NOT_A_STELLAR_KEY"

    assert validate_evm_address(valid_evm)
    assert not validate_evm_address(invalid_evm)
    assert validate_stellar_address(valid_stellar)
    assert not validate_stellar_address(invalid_stellar)


def test_deterministic_settlement_receipt_generation():
    """Verify that settlement engine outputs deterministic SHA-256 transaction receipt."""
    engine = BountySettlementEngine(nominal_usd="3000.00")
    res1 = engine.compute_settlement(
        evm_recipient="0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89",
        stellar_recipient="GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC",
        issue_id=1589,
    )
    res2 = engine.compute_settlement(
        evm_recipient="0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89",
        stellar_recipient="GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC",
        issue_id=1589,
    )

    assert len(res1["tx_hash"]) == 64
    assert res1["tx_hash"] == res2["tx_hash"]
