"""Unit tests for Equal-Count Parallel Welford Reduction Optimization (Issue #604).
Validates:
- Mathematical equivalence between General Welford and Equal-Count Welford.
- Complete elimination of runtime floating-point divisions during equal-tile merges.
- Numerical precision matching numpy population variance and mean within 1e-6 tolerance.
- Multi-core hierarchical GroupNorm reduction tree simulation.
"""

import math
import numpy as np
import pytest
from scripts.equal_count_welford import (
    WelfordState,
    GeneralParallelWelford,
    EqualCountOptimizedWelford,
)


def test_equal_count_vs_general_welford_equivalence():
    tile_size = 512
    rng = np.random.default_rng(42)
    tile_a = rng.normal(10.0, 2.5, tile_size).astype(np.float64)
    tile_b = rng.normal(14.0, 3.1, tile_size).astype(np.float64)

    # General parallel welford
    gen_a = GeneralParallelWelford.compute_tile(tile_a)
    gen_b = GeneralParallelWelford.compute_tile(tile_b)
    merged_gen, div_ops = GeneralParallelWelford.merge(gen_a, gen_b)
    assert div_ops == 2  # General merge required 2 runtime divisions

    # Equal-count optimized welford
    opt = EqualCountOptimizedWelford(tile_size=tile_size)
    opt_a = opt.compute_equal_tile(tile_a)
    opt_b = opt.compute_equal_tile(tile_b)
    merged_opt, opt_div_ops = opt.merge_equal(opt_a, opt_b)
    assert opt_div_ops == 0  # Zero runtime divisions!

    # Validate mathematical equivalence
    assert math.isclose(merged_gen.mean, merged_opt.mean, rel_tol=1e-9)
    assert math.isclose(merged_gen.m2, merged_opt.m2, rel_tol=1e-9)
    assert math.isclose(merged_gen.variance, merged_opt.variance, rel_tol=1e-9)
    assert merged_gen.count == merged_opt.count == (2 * tile_size)


def test_numerical_accuracy_against_numpy_ground_truth():
    tile_size = 1024
    rng = np.random.default_rng(2026)
    combined_data = rng.uniform(-100.0, 100.0, 2 * tile_size).astype(np.float64)
    tile_a = combined_data[:tile_size]
    tile_b = combined_data[tile_size:]

    gt_mean = float(np.mean(combined_data))
    gt_var = float(np.var(combined_data))

    opt = EqualCountOptimizedWelford(tile_size=tile_size)
    state_a = opt.compute_equal_tile(tile_a)
    state_b = opt.compute_equal_tile(tile_b)
    merged, div_ops = opt.merge_equal(state_a, state_b)

    assert div_ops == 0
    assert math.isclose(merged.mean, gt_mean, rel_tol=1e-8)
    assert math.isclose(merged.population_variance, gt_var, rel_tol=1e-8)


def test_hierarchical_groupnorm_reduction_tree():
    num_cores = 8
    tile_size = 256
    rng = np.random.default_rng(777)
    tiles = [rng.normal(5.0, 1.5, tile_size).astype(np.float64) for _ in range(num_cores)]
    full_array = np.concatenate(tiles)

    gt_mean = float(np.mean(full_array))
    gt_var = float(np.var(full_array))

    opt = EqualCountOptimizedWelford(tile_size=tile_size)
    tree_res = opt.hierarchical_groupnorm_reduction(tiles)

    assert tree_res["runtime_fp_divisions"] == 0
    assert math.isclose(tree_res["mean"], gt_mean, rel_tol=1e-7)
    assert math.isclose(tree_res["variance"], gt_var, rel_tol=1e-7)
    assert tree_res["rsqrt_var"] > 0
    assert tree_res["cycles_saved_pct"] >= 36.0


def test_welford_state_edge_cases():
    s0 = WelfordState(mean=0.0, m2=0.0, count=0)
    assert s0.variance == 0.0
    assert s0.population_variance == 0.0

    s1 = WelfordState(mean=5.0, m2=0.0, count=1)
    assert s1.variance == 0.0
    assert s1.population_variance == 0.0
