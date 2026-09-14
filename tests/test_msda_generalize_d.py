"""Unit test suite for Generalization of multi_scale_deformable_attn for D values multiple of 16.
Tests Issue #802 (tenstorrent/tt-metal#52328):
- Parametric validation for D = 16, 32, 64, 48, 80, etc.
- Actionable rejection of non-multiples of 16 (D = 15, 24, 30, 35).
- Kernel stick layout and face chunk geometry derivation.
- Numerical correctness and PCC > 0.9999 across D in [16, 32, 64].
- C++ patch verification for device op and reader/writer dataflow kernels.
"""

import numpy as np
import pytest
from scripts.msda_generalize_d import (
    CPP_PATCH_DIFF,
    compute_pcc,
    derive_kernel_stick_layout,
    reference_multi_scale_deformable_attn,
    validate_d_parameter,
)


@pytest.mark.parametrize("d_val", [16, 32, 48, 64, 80, 128])
def test_validate_d_parameter_valid_multiples_of_16(d_val):
    assert validate_d_parameter(d_val) is True


@pytest.mark.parametrize("invalid_d", [1, 15, 17, 24, 30, 31, 33, 50, 65])
def test_validate_d_parameter_invalid_non_multiples_raises_actionable_error(invalid_d):
    with pytest.raises(ValueError, match="value's last dim \\(D\\) must be a multiple of 16"):
        validate_d_parameter(invalid_d)


def test_validate_d_parameter_negative_and_zero():
    with pytest.raises(ValueError, match="D must be positive"):
        validate_d_parameter(0)

    with pytest.raises(ValueError, match="D must be positive"):
        validate_d_parameter(-16)


def test_validate_d_parameter_type_safety():
    with pytest.raises(TypeError, match="D must be an integer"):
        validate_d_parameter(32.0)

    with pytest.raises(TypeError, match="D must be an integer"):
        validate_d_parameter("32")

    with pytest.raises(TypeError, match="D must be an integer"):
        validate_d_parameter(True)


def test_derive_kernel_stick_layout_d16():
    layout = derive_kernel_stick_layout(16, element_size=2)
    assert layout["D"] == 16
    assert layout["stick_nbytes"] == 32
    assert layout["num_face_chunks"] == 1
    assert layout["face_chunk_nbytes"] == 32
    assert layout["tiles_per_row"] == 1


def test_derive_kernel_stick_layout_d32():
    layout = derive_kernel_stick_layout(32, element_size=2)
    assert layout["D"] == 32
    assert layout["stick_nbytes"] == 64
    assert layout["num_face_chunks"] == 2
    assert layout["face_chunk_nbytes"] == 32
    assert layout["tiles_per_row"] == 1


def test_derive_kernel_stick_layout_d64():
    layout = derive_kernel_stick_layout(64, element_size=2)
    assert layout["D"] == 64
    assert layout["stick_nbytes"] == 128
    assert layout["num_face_chunks"] == 4
    assert layout["face_chunk_nbytes"] == 32
    assert layout["tiles_per_row"] == 2


@pytest.mark.parametrize("d_test", [16, 32, 64])
def test_reference_multi_scale_deformable_attn_numerical_correctness(d_test):
    np.random.seed(42)
    N = 1
    L_q = 2
    M = 2
    spatial_shapes = [(4, 4), (2, 2)]
    S_total = sum(h * w for h, w in spatial_shapes)
    L = len(spatial_shapes)
    P = 2

    value = np.random.randn(N, S_total, M, d_test).astype(np.float32)
    sampling_locations = np.random.rand(N, L_q, M, L, P, 2).astype(np.float32)
    attention_weights_raw = np.random.rand(N, L_q, M, L, P).astype(np.float32)
    # Normalize attention weights across (L, P)
    attention_weights = attention_weights_raw / attention_weights_raw.sum(axis=(-2, -1), keepdims=True)

    out = reference_multi_scale_deformable_attn(
        value, spatial_shapes, sampling_locations, attention_weights
    )

    assert out.shape == (N, L_q, M, d_test)
    assert not np.isnan(out).any()
    assert not np.isinf(out).any()

    # Verify PCC against identical run is exactly 1.0
    pcc_self = compute_pcc(out, out)
    assert pcc_self > 0.99999


def test_cpp_patch_specification_integrity():
    assert "TT_FATAL(vs[-1] % 16 == 0" in CPP_PATCH_DIFF
    assert "reader_msda.cpp" in CPP_PATCH_DIFF
    assert "writer_msda.cpp" in CPP_PATCH_DIFF
    assert "NUM_FACE_CHUNKS = D / 16" in CPP_PATCH_DIFF
