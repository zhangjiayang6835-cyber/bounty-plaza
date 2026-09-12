"""Comprehensive test suite for Issue #1472 legacy path removals.

Verifies complete elimination of legacy sqrt, rsqrt, and reciprocal compatibility paths,
validating numerical precision, architecture coverage, normalization kernels,
model configurations, and zero-legacy static verification.
"""

import math
import os
import pytest

from packages.tt_metal_precision_kernels.kernels import (
    compute_reciprocal,
    compute_rsqrt,
    compute_sqrt,
    quantize_bf16,
    recip_tile,
    rsqrt_tile,
    sqrt_tile,
)
from packages.tt_metal_precision_kernels.legacy_scanner import (
    scan_codebase_directory,
    scan_source_text,
)
from packages.tt_metal_precision_kernels.model_configs import (
    ModelArchitecture,
    get_canonical_model_config,
    migrate_legacy_config,
)
from packages.tt_metal_precision_kernels.normalization import (
    distributed_rms_norm,
    group_norm,
    layer_norm,
    rms_norm,
)
from packages.tt_metal_precision_kernels.sdpa import (
    sampling_recip_scalar,
    scaled_dot_product_attention,
    softmax,
)
from packages.tt_metal_precision_kernels.types import (
    Architecture,
    DType,
    GroupNormConfig,
    LayerNormConfig,
    PrecisionMode,
    RMSNormConfig,
    SDPAConfig,
)


def test_reciprocal_precise_fp32() -> None:
    """Verify FP32 precise reciprocal accuracy across typical positive and negative values."""
    test_values = [0.1, 0.5, 1.0, 2.0, 4.0, 10.0, 100.0, -0.2, -1.0, -5.0]
    for val in test_values:
        res = compute_reciprocal(val, mode=PrecisionMode.PRECISE, dtype=DType.FP32)
        expected = 1.0 / val
        assert math.isclose(res, expected, rel_tol=1e-6)


def test_reciprocal_approximate_modes() -> None:
    """Verify approximate reciprocal across Wormhole and Blackhole architectures."""
    test_values = [0.25, 0.5, 1.0, 2.0, 8.0, 16.0]
    for arch in (Architecture.WORMHOLE_B0, Architecture.BLACKHOLE):
        for val in test_values:
            res = compute_reciprocal(
                val, mode=PrecisionMode.APPROXIMATE, dtype=DType.FP32, arch=arch
            )
            expected = 1.0 / val
            assert math.isclose(res, expected, rel_tol=1e-2)


def test_reciprocal_edge_cases() -> None:
    """Verify IEEE 754 edge cases including zero, infinity, and NaN for reciprocal."""
    pos_zero_res = compute_reciprocal(0.0)
    assert math.isinf(pos_zero_res) and pos_zero_res > 0.0

    neg_zero_res = compute_reciprocal(-0.0)
    assert math.isinf(neg_zero_res) and neg_zero_res < 0.0

    pos_inf_res = compute_reciprocal(float("inf"))
    assert pos_inf_res == 0.0

    neg_inf_res = compute_reciprocal(float("-inf"))
    assert neg_inf_res == -0.0

    nan_res = compute_reciprocal(float("nan"))
    assert math.isnan(nan_res)


def test_sqrt_precise_and_approximate() -> None:
    """Verify sqrt calculations across precise and approximate modes for normal positive inputs."""
    test_values = [0.01, 0.25, 1.0, 4.0, 9.0, 16.0, 100.0, 1024.0]
    for val in test_values:
        precise_res = compute_sqrt(val, mode=PrecisionMode.PRECISE, dtype=DType.FP32)
        expected = math.sqrt(val)
        assert math.isclose(precise_res, expected, rel_tol=1e-6)

        approx_wh = compute_sqrt(
            val, mode=PrecisionMode.APPROXIMATE, dtype=DType.FP32, arch=Architecture.WORMHOLE_B0
        )
        assert math.isclose(approx_wh, expected, rel_tol=2e-2)

        approx_bh = compute_sqrt(
            val, mode=PrecisionMode.APPROXIMATE, dtype=DType.FP32, arch=Architecture.BLACKHOLE
        )
        assert math.isclose(approx_bh, expected, rel_tol=1e-2)


def test_sqrt_edge_cases() -> None:
    """Verify square root edge cases including negative values, zero, infinity, and NaN."""
    assert compute_sqrt(0.0) == 0.0
    assert compute_sqrt(-0.0) == 0.0
    assert math.isinf(compute_sqrt(float("inf")))
    assert math.isnan(compute_sqrt(-4.0))
    assert math.isnan(compute_sqrt(float("nan")))


def test_rsqrt_precise_and_approximate() -> None:
    """Verify reciprocal square root across architectures and precision settings."""
    test_values = [0.04, 0.25, 1.0, 4.0, 16.0, 64.0, 256.0]
    for val in test_values:
        precise = compute_rsqrt(val, mode=PrecisionMode.PRECISE, dtype=DType.FP32)
        expected = 1.0 / math.sqrt(val)
        assert math.isclose(precise, expected, rel_tol=1e-6)

        approx = compute_rsqrt(
            val, mode=PrecisionMode.APPROXIMATE, dtype=DType.FP32, arch=Architecture.BLACKHOLE
        )
        assert math.isclose(approx, expected, rel_tol=2e-2)


def test_rsqrt_edge_cases() -> None:
    """Verify rsqrt edge cases for domain errors, singularity, and infinities."""
    assert math.isinf(compute_rsqrt(0.0))
    assert compute_rsqrt(float("inf")) == 0.0
    assert math.isnan(compute_rsqrt(-1.0))
    assert math.isnan(compute_rsqrt(float("nan")))


def test_bf16_quantization_and_destinations() -> None:
    """Verify bfloat16 quantization characteristics and destination format behavior."""
    assert math.isnan(quantize_bf16(float("nan")))
    assert math.isinf(quantize_bf16(float("inf")))
    assert quantize_bf16(0.0) == 0.0

    val = 3.1415926535
    bf16_val = quantize_bf16(val)
    assert abs(bf16_val - val) < 0.02

    recip_bf16 = compute_reciprocal(2.0, mode=PrecisionMode.PRECISE, dtype=DType.BF16)
    assert math.isclose(recip_bf16, 0.5, rel_tol=1e-3)

    sqrt_bf16 = compute_sqrt(4.0, mode=PrecisionMode.PRECISE, dtype=DType.BF16)
    assert math.isclose(sqrt_bf16, 2.0, rel_tol=1e-3)


def test_tile_operations() -> None:
    """Verify element-wise 2D tile execution for recip, sqrt, and rsqrt."""
    tile = [[1.0, 4.0], [9.0, 16.0]]
    recip_res = recip_tile(tile, mode=PrecisionMode.PRECISE)
    assert math.isclose(recip_res[0][0], 1.0)
    assert math.isclose(recip_res[0][1], 0.25)

    sqrt_res = sqrt_tile(tile, mode=PrecisionMode.PRECISE)
    assert math.isclose(sqrt_res[1][0], 3.0)
    assert math.isclose(sqrt_res[1][1], 4.0)

    rsqrt_res = rsqrt_tile(tile, mode=PrecisionMode.PRECISE)
    assert math.isclose(rsqrt_res[0][1], 0.5)
    assert math.isclose(rsqrt_res[1][1], 0.25)


def test_legacy_configuration_rejection() -> None:
    """Verify that obsolete legacy_rsqrt parameter is strictly rejected across all configs."""
    with pytest.raises(ValueError) as exc_ln:
        LayerNormConfig(legacy_rsqrt=True)
    assert "legacy_rsqrt" in str(exc_ln.value)

    with pytest.raises(ValueError) as exc_rms:
        RMSNormConfig(legacy_rsqrt=True)
    assert "legacy_rsqrt" in str(exc_rms.value)

    with pytest.raises(ValueError) as exc_sdpa:
        SDPAConfig(legacy_rsqrt=True)
    assert "legacy_rsqrt" in str(exc_sdpa.value)

    with pytest.raises(ValueError) as exc_gn:
        GroupNormConfig(legacy_rsqrt=True)
    assert "legacy_rsqrt" in str(exc_gn.value)


def test_layernorm_execution() -> None:
    """Verify LayerNorm executes with standard and Welford variance paths."""
    inputs = [1.0, 2.0, 3.0, 4.0, 5.0]
    gamma = [1.0] * 5
    beta = [0.0] * 5

    config_standard = LayerNormConfig(
        eps=1e-5, precision_mode=PrecisionMode.PRECISE, use_welford=False
    )
    out_standard = layer_norm(inputs, gamma, beta, config_standard)
    assert len(out_standard) == 5
    assert math.isclose(sum(out_standard), 0.0, abs_tol=1e-5)

    config_welford = LayerNormConfig(
        eps=1e-5, precision_mode=PrecisionMode.PRECISE, use_welford=True
    )
    out_welford = layer_norm(inputs, gamma, beta, config_welford)
    assert len(out_welford) == 5
    for std_val, welf_val in zip(out_standard, out_welford):
        assert math.isclose(std_val, welf_val, rel_tol=1e-4)


def test_rmsnorm_execution() -> None:
    """Verify RMSNorm produces expected normalized magnitude without legacy flags."""
    inputs = [2.0, -2.0, 2.0, -2.0]
    weights = [1.0, 1.0, 1.0, 1.0]
    config = RMSNormConfig(eps=1e-6, precision_mode=PrecisionMode.PRECISE)
    outputs = rms_norm(inputs, weights, config)
    assert len(outputs) == 4
    for val in outputs:
        assert math.isclose(abs(val), 1.0, rel_tol=1e-4)


def test_group_norm_execution() -> None:
    """Verify GroupNorm partitions sequence into groups and applies canonical rsqrt."""
    inputs = [1.0, 2.0, 3.0, 4.0]
    gamma = [1.0] * 4
    beta = [0.0] * 4
    config = GroupNormConfig(num_groups=2, eps=1e-5, precision_mode=PrecisionMode.PRECISE)
    outputs = group_norm(inputs, gamma, beta, config)
    assert len(outputs) == 4
    assert math.isclose(outputs[0] + outputs[1], 0.0, abs_tol=1e-4)
    assert math.isclose(outputs[2] + outputs[3], 0.0, abs_tol=1e-4)


def test_distributed_rms_norm_execution() -> None:
    """Verify distributed RMSNorm correctly simulates multi-device shard reduction."""
    shard0 = [2.0, 2.0]
    shard1 = [2.0, 2.0]
    weights = [1.0, 1.0]
    config = RMSNormConfig(eps=1e-6, precision_mode=PrecisionMode.PRECISE)
    res_shards = distributed_rms_norm([shard0, shard1], weights, config)
    assert len(res_shards) == 2
    for shard in res_shards:
        for elem in shard:
            assert math.isclose(elem, 1.0, rel_tol=1e-4)


def test_sdpa_and_sampling() -> None:
    """Verify Scaled Dot-Product Attention and probability sampling."""
    queries = [[1.0, 0.0], [0.0, 1.0]]
    keys = [[1.0, 0.0], [0.0, 1.0]]
    values = [[0.5, 1.5], [2.5, 3.5]]
    sdpa_cfg = SDPAConfig(scale=1.0, precision_mode=PrecisionMode.PRECISE)

    sm_res = softmax([1.0, 2.0], sdpa_cfg)
    assert math.isclose(sum(sm_res), 1.0, rel_tol=1e-5)

    attn_out = scaled_dot_product_attention(queries, keys, values, sdpa_cfg)
    assert len(attn_out) == 2
    assert len(attn_out[0]) == 2

    probs = [0.2, 0.3, 0.5]
    norm_probs = sampling_recip_scalar(probs, sdpa_cfg)
    assert math.isclose(sum(norm_probs), 1.0, rel_tol=1e-5)


def test_model_configuration_migration() -> None:
    """Verify migration of legacy model configs removing legacy_rsqrt."""
    raw_falcon = {
        "model_name": "Falcon-7B",
        "legacy_rsqrt": True,
        "legacy_compat": True,
        "hidden_size": 4544,
    }
    migrated = migrate_legacy_config(raw_falcon)
    assert "legacy_rsqrt" not in migrated
    assert "legacy_compat" not in migrated
    assert migrated["precision_mode"] == PrecisionMode.PRECISE

    falcon_cfg = get_canonical_model_config(ModelArchitecture.FALCON_7B)
    assert falcon_cfg.precision_mode == PrecisionMode.PRECISE
    assert falcon_cfg.norm_eps == 1e-5

    bge_cfg = get_canonical_model_config(ModelArchitecture.BGE_LARGE)
    assert bge_cfg.precision_mode == PrecisionMode.PRECISE
    assert bge_cfg.use_welford is True


def test_static_scanner_catches_legacy_tokens() -> None:
    """Verify legacy scanner detects prohibited symbols in offending snippets."""
    bad_code = "def bad_function(): return legacy_rsqrt(4.0)"
    violations = scan_source_text(bad_code, filename="bad.py")
    assert len(violations) > 0

    bad_include = '#include "ckernel_sfpu_rsqrt_compat.h"'
    violations_inc = scan_source_text(bad_include, filename="bad.cpp")
    assert len(violations_inc) > 0


def test_packages_have_zero_legacy_symbols() -> None:
    """Audit the packages directory to confirm zero legacy compatibility tokens remain."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_dir = os.path.join(base_dir, "packages", "tt_metal_precision_kernels")
    findings = scan_codebase_directory(target_dir)
    clean_findings = {k: v for k, v in findings.items() if not k.endswith("legacy_scanner.py")}
    assert len(clean_findings) == 0
