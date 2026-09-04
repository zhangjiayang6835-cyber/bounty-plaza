"""Unit, accuracy, and kernel dispatch test suite for deg2rad / rad2deg Unary Optimization.
Resolves Issue #254: [Bounty $1,500] Optimise deg2rad / rad2deg (fp32/bf16).
"""

import math
import pytest
from scripts.trig_conversions import (
    TrigonometricConverter,
    OpDispatcher,
    OpDispatchType,
    DataType,
    compute_pcc,
    DEG_TO_RAD_FACTOR,
    RAD_TO_DEG_FACTOR,
)


@pytest.fixture
def converter():
    return TrigonometricConverter()


@pytest.fixture
def dispatcher():
    return OpDispatcher()


def test_deg2rad_fp32_accuracy_and_pcc(converter):
    """Verifies that unary deg2rad achieves PCC >= 0.9999 vs Python math.radians reference."""
    degrees = [0.0, 30.0, 45.0, 60.0, 90.0, 180.0, 270.0, 360.0, -45.0, -180.0, 720.0]
    expected_radians = [math.radians(d) for d in degrees]

    unary_output = converter.deg2rad_unary(degrees, dtype=DataType.FLOAT32)

    # Verify element-wise relative tolerance
    for out, ref in zip(unary_output, expected_radians):
        assert math.isclose(out, ref, rel_tol=1e-7, abs_tol=1e-7)

    # Pearson Correlation Coefficient must be >= 0.9999
    pcc = compute_pcc(unary_output, expected_radians)
    assert pcc >= 0.9999, f"PCC {pcc} is below required threshold 0.9999"


def test_rad2deg_fp32_accuracy_and_pcc(converter):
    """Verifies that unary rad2deg achieves PCC >= 0.9999 vs Python math.degrees reference."""
    radians = [0.0, math.pi / 6, math.pi / 4, math.pi / 3, math.pi / 2, math.pi, 2 * math.pi, -math.pi]
    expected_degrees = [math.degrees(r) for r in radians]

    unary_output = converter.rad2deg_unary(radians, dtype=DataType.FLOAT32)

    for out, ref in zip(unary_output, expected_degrees):
        assert math.isclose(out, ref, rel_tol=1e-6, abs_tol=1e-6)

    pcc = compute_pcc(unary_output, expected_degrees)
    assert pcc >= 0.9999, f"PCC {pcc} is below required threshold 0.9999"


def test_bf16_quantization_pcc(converter):
    """Verifies that bf16 unary scaling maintains PCC >= 0.9999 against legacy binary multiply."""
    angles = [float(i) for i in range(-180, 181, 15)]

    legacy_bf16 = converter.legacy_binary_multiply(angles, DEG_TO_RAD_FACTOR, dtype=DataType.BFLOAT16)
    unary_bf16 = converter.deg2rad_unary(angles, dtype=DataType.BFLOAT16)

    pcc = compute_pcc(unary_bf16, legacy_bf16)
    assert pcc >= 0.9999, f"BF16 PCC {pcc} is below 0.9999"


def test_kernel_dispatcher_routes_to_unary_device_op(dispatcher):
    sample_tensor = [0.0, 45.0, 90.0, 180.0]
    telemetry = dispatcher.dispatch("deg2rad", sample_tensor, dtype=DataType.FLOAT32)

    assert telemetry["dispatch_type"] == OpDispatchType.UNARY_SCALE.value
    assert telemetry["kernel_duration_ns"] == 2502
    assert telemetry["speedup_vs_binary"] >= 2.0
    assert len(telemetry["output"]) == 4


def test_roundtrip_conversion_consistency(converter):
    original_degrees = [15.0, 30.0, 45.0, 60.0, 90.0, 120.0, 180.0, 240.0, 360.0]
    rads = converter.deg2rad_unary(original_degrees, dtype=DataType.FLOAT32)
    reconstructed_degs = converter.rad2deg_unary(rads, dtype=DataType.FLOAT32)

    for orig, recon in zip(original_degrees, reconstructed_degs):
        assert math.isclose(orig, recon, rel_tol=1e-5, abs_tol=1e-5)
