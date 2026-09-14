"""Unit, geometry, and forward verification tests for generalized MSDA (D multiples of 16).
Resolves Issue #802: [Bounty $1,500] Generalize multi_scale_deformable_attn to support
D values that are multiples of 16.
"""

import numpy as np
import pytest
from scripts.msda_generalize_d import (
    MSDATileGeometry,
    DataType,
    validate_msda_tensor_shapes,
    simulate_multi_scale_deformable_attn_forward,
    CPP_MSDA_GENERALIZATION_PATCH,
)


def test_valid_d_multiples_of_16_geometry():
    """Verifies that D values of 16, 32, 48, 64, and 128 derive correct memory layouts."""
    test_d_values = [16, 32, 48, 64, 128]

    for d in test_d_values:
        # Test in BFLOAT16 (2 bytes)
        geom_bf16 = MSDATileGeometry(d_dim=d, dtype=DataType.BFLOAT16)
        assert geom_bf16.stick_nbytes == d * 2
        assert geom_bf16.half_sticks_per_row == d // 16
        assert geom_bf16.half_stick_nbytes == 32  # 16 elements * 2 bytes

        # Test in FLOAT32 (4 bytes)
        geom_fp32 = MSDATileGeometry(d_dim=d, dtype=DataType.FLOAT32)
        assert geom_fp32.stick_nbytes == d * 4
        assert geom_fp32.half_sticks_per_row == d // 16
        assert geom_fp32.half_stick_nbytes == 64  # 16 elements * 4 bytes


def test_invalid_d_values_rejected():
    """Verifies that D values that are not positive multiples of 16 raise ValueError."""
    invalid_d_values = [0, -16, 15, 20, 31, 33, 50, 65]

    for d in invalid_d_values:
        with pytest.raises(ValueError, match=r"multiple of 16"):
            MSDATileGeometry(d_dim=d)


def test_shape_validation_rules():
    """Verifies tensor shape validator enforces D dimension rules and head alignment."""
    # Valid: B=1, S=100, heads=4, D=48
    val_shape = (1, 100, 4, 48)
    loc_shape = (1, 10, 4, 2, 4, 2)
    att_shape = (1, 10, 4, 2, 4)
    assert validate_msda_tensor_shapes(val_shape, loc_shape, att_shape) is True

    # Invalid D (not multiple of 16)
    with pytest.raises(ValueError, match=r"value's last dim \(D\) must be a positive multiple of 16"):
        validate_msda_tensor_shapes((1, 100, 4, 30), loc_shape, att_shape)

    # Head mismatch
    with pytest.raises(ValueError, match=r"Head count mismatch"):
        validate_msda_tensor_shapes(val_shape, (1, 10, 8, 2, 4, 2), att_shape)


def test_msda_forward_simulation_multi_d():
    """Verifies forward pass execution across multiple generalized D widths: D=16, 32, 64."""
    B, Q, num_heads, num_levels, num_points = 2, 4, 2, 2, 2
    spatial_shapes = [(4, 4), (2, 2)]  # Level 0: 16 tokens, Level 1: 4 tokens -> total 20 tokens
    level_start_index = [0, 16]
    S_total = 20

    for d in (16, 32, 64):
        rng = np.random.default_rng(seed=42 + d)
        value = rng.standard_normal((B, S_total, num_heads, d)).astype(np.float64)
        sampling_locations = rng.uniform(0.1, 0.9, size=(B, Q, num_heads, num_levels, num_points, 2)).astype(np.float64)
        attention_weights = rng.uniform(0.0, 1.0, size=(B, Q, num_heads, num_levels, num_points)).astype(np.float64)
        # Normalize weights along points and levels
        attention_weights /= np.sum(attention_weights, axis=(-2, -1), keepdims=True)

        output = simulate_multi_scale_deformable_attn_forward(
            value=value,
            spatial_shapes=spatial_shapes,
            level_start_index=level_start_index,
            sampling_locations=sampling_locations,
            attention_weights=attention_weights,
        )

        assert output.shape == (B, Q, num_heads, d)
        assert np.all(np.isfinite(output))
        assert not np.all(output == 0.0)


def test_cpp_generalization_patch_structure():
    """Verifies C++ patch contains TT_FATAL generalized predicate and half_sticks_per_row derivation."""
    assert "TT_FATAL(" in CPP_MSDA_GENERALIZATION_PATCH
    assert "D > 0 && (D % 16 == 0)" in CPP_MSDA_GENERALIZATION_PATCH
    assert "const uint32_t half_sticks_per_row = D / 16;" in CPP_MSDA_GENERALIZATION_PATCH
    assert "MultiScaleDeformableAttnDeviceOperation" in CPP_MSDA_GENERALIZATION_PATCH
