"""Comprehensive verification suite for ttnn.quantize and requantize uint8 saturation."""

from pathlib import Path
import pytest
from packages.ttnn_quantize_saturation import (
    DataType,
    Architecture,
    RequantConfig,
    quantize,
    requantize,
    quantize_element,
    requantize_element,
    dequantize_element,
    narrow_composite_result,
    is_narrow_quantized_dtype,
    SFPUSimulator,
    SFPURegisterState,
    WH_QUANT_REPLAY_LEN_UINT8_OUT,
    WH_REQUANT_REPLAY_LEN_UINT8_OUT,
    BH_QUANT_REPLAY_LEN_UINT8_OUT,
    BH_REQUANT_REPLAY_LEN_UINT8_2S_COMP,
    BH_REQUANT_REPLAY_LEN_UINT8_SIGN_MAGN,
)


def test_quantize_uint8_negative_saturation() -> None:
    """Verifies that negative floating point inputs saturate strictly to zero for uint8."""
    negative_inputs = [-100.0, -10.0, -2.0, -1.0, -0.5, -0.1]
    for val in negative_inputs:
        result = quantize(val, scale=1.0, zero_point=0, dtype=DataType.UINT8)
        assert result == 0


def test_quantize_uint8_asymmetry_with_magnitude() -> None:
    """Verifies that negative inputs do not produce their absolute positive magnitude."""
    test_values = [1.0, 5.0, 10.0, 50.0, 120.0]
    for val in test_values:
        positive_result = quantize(val, scale=1.0, zero_point=0, dtype=DataType.UINT8)
        negative_result = quantize(-val, scale=1.0, zero_point=0, dtype=DataType.UINT8)
        assert positive_result == int(val)
        assert negative_result == 0


def test_quantize_uint8_upper_bound_saturation() -> None:
    """Verifies that large positive values saturate at the uint8 maximum of 255."""
    large_inputs = [255.0, 255.4, 255.6, 256.0, 300.0, 1000.0, 1e6]
    for val in large_inputs:
        result = quantize(val, scale=1.0, zero_point=0, dtype=DataType.UINT8)
        assert result == 255


def test_quantize_uint8_in_range_rounding() -> None:
    """Verifies accurate round-ties-to-even behavior for values inside [0, 255]."""
    cases = [
        (0.0, 0),
        (0.4, 0),
        (0.6, 1),
        (1.5, 2),
        (2.5, 2),
        (3.5, 4),
        (10.2, 10),
        (10.8, 11),
        (254.4, 254),
        (254.6, 255),
    ]
    for val, expected in cases:
        result = quantize(val, scale=1.0, zero_point=0, dtype=DataType.UINT8)
        assert result == expected


def test_quantize_uint8_with_zero_point_offsets() -> None:
    """Verifies quantization lower saturation when scale and zero-point are configured."""
    scale = 2.0
    zero_point = 10

    assert quantize(-20.0, scale=scale, zero_point=zero_point, dtype=DataType.UINT8) == 0
    assert quantize(-25.0, scale=scale, zero_point=zero_point, dtype=DataType.UINT8) == 0
    assert quantize(-10.0, scale=scale, zero_point=zero_point, dtype=DataType.UINT8) == 5
    assert quantize(0.0, scale=scale, zero_point=zero_point, dtype=DataType.UINT8) == 10
    assert quantize(20.0, scale=scale, zero_point=zero_point, dtype=DataType.UINT8) == 20


def test_requantize_uint8_lower_saturation_issue_spec() -> None:
    """Verifies requantization saturation matching the upstream issue specification."""
    in_scale = 2.0
    in_zp = 10
    out_scale = 1.0
    out_zp = 5

    inputs = [0, 5, 10, 20, 100]
    expected_outputs = [0, 0, 5, 25, 185]

    config = RequantConfig(in_scale, in_zp, out_scale, out_zp, DataType.UINT8)
    outputs = [requantize_element(x, config) for x in inputs]
    assert outputs == expected_outputs

    tensor_output = requantize(
        inputs,
        in_scale=in_scale,
        in_zero_point=in_zp,
        out_scale=out_scale,
        out_zero_point=out_zp,
        dtype=DataType.UINT8,
    )
    assert tensor_output == expected_outputs


def test_requantize_uint8_nested_tensors() -> None:
    """Verifies multi-dimensional tensor handling during requantization."""
    tensor_2d = [
        [0, 2, 4],
        [6, 8, 10],
    ]
    config = RequantConfig(
        in_scale=1.0,
        in_zero_point=5,
        out_scale=1.0,
        out_zero_point=0,
        dtype=DataType.UINT8,
    )
    result = requantize(tensor_2d, config)
    assert result == [
        [0, 0, 0],
        [1, 3, 5],
    ]


def test_requantize_int8_in_uint8_out() -> None:
    """Verifies requantization from signed int8 input range into saturated uint8."""
    int8_inputs = [-128, -50, -10, 0, 10, 50, 127]
    config = RequantConfig(
        in_scale=1.0,
        in_zero_point=0,
        out_scale=1.0,
        out_zero_point=10,
        dtype=DataType.UINT8,
    )
    result = requantize(int8_inputs, config)
    assert result[0] == 0
    assert result[1] == 0
    assert result[2] == 0
    assert result[3] == 10
    assert result[4] == 20
    assert result[5] == 60
    assert result[6] == 137


def test_int8_preservation() -> None:
    """Verifies that signed int8 quantization continues to clamp to [-128, 127]."""
    cases = [
        (-200.0, -128),
        (-128.0, -128),
        (0.0, 0),
        (127.0, 127),
        (200.0, 127),
    ]
    for val, expected in cases:
        result = quantize(val, scale=1.0, zero_point=0, dtype=DataType.INT8)
        assert result == expected


def test_sfpu_hardware_wormhole_b0_replay_and_clamp() -> None:
    """Verifies Wormhole B0 replay buffer lengths and clamp instruction execution."""
    simulator = SFPUSimulator(Architecture.WORMHOLE_B0)
    assert simulator.get_quant_replay_length() == WH_QUANT_REPLAY_LEN_UINT8_OUT
    assert simulator.get_requant_replay_length() == WH_REQUANT_REPLAY_LEN_UINT8_OUT

    negative_out = simulator.execute_quant_element(input_fp=-5.0, scale=1.0, zero_point=0)
    assert negative_out == 0

    config = RequantConfig(1.0, 10, 1.0, 0, DataType.UINT8)
    requant_out = simulator.execute_requant_element(input_int=2, config=config)
    assert requant_out == 0


def test_sfpu_hardware_blackhole_replay_and_clamp() -> None:
    """Verifies Blackhole replay buffer lengths and clamp instruction execution."""
    simulator = SFPUSimulator(Architecture.BLACKHOLE)
    assert simulator.get_quant_replay_length() == BH_QUANT_REPLAY_LEN_UINT8_OUT
    requant_2s = simulator.get_requant_replay_length(int8_input=False)
    assert requant_2s == BH_REQUANT_REPLAY_LEN_UINT8_2S_COMP
    requant_sm = simulator.get_requant_replay_length(int8_input=True)
    assert requant_sm == BH_REQUANT_REPLAY_LEN_UINT8_SIGN_MAGN

    negative_out = simulator.execute_quant_element(input_fp=-25.0, scale=1.0, zero_point=0)
    assert negative_out == 0


def test_sfpu_raw_hardware_reproduction_of_bug() -> None:
    """Demonstrates that un-clamped hardware conversion incorrectly returns positive magnitude."""
    state = SFPURegisterState()
    state.lreg0 = -15.0

    raw_buggy_result = state.raw_fp32_to_uint8_without_clamp()
    assert raw_buggy_result == 15

    clamped_fixed_result = state.uint8_round()
    assert clamped_fixed_result == 0


def test_composite_narrowing_prevents_modular_wrapping() -> None:
    """Verifies that composite narrowing routes through saturating quantize for uint8."""
    assert is_narrow_quantized_dtype(DataType.UINT8)
    assert is_narrow_quantized_dtype(DataType.INT8)
    assert not is_narrow_quantized_dtype(DataType.FLOAT32)

    shifted_negative = [-20.0, -5.0, 0.0, 10.0, 300.0]
    result = narrow_composite_result(shifted_negative, DataType.UINT8)

    assert result[0] == 0
    assert result[1] == 0
    assert result[2] == 0
    assert result[3] == 10
    assert result[4] == 255


def test_quantize_dequantize_roundtrip() -> None:
    """Verifies end-to-end roundtrip fidelity for valid in-range uint8 representations."""
    scale = 0.5
    zero_point = 20
    test_ints = [0, 10, 50, 100, 200, 255]

    for original_int in test_ints:
        fp_val = dequantize_element(original_int, scale, zero_point)
        quantized_int = quantize_element(fp_val, scale, zero_point, DataType.UINT8)
        assert quantized_int == original_int


def test_edge_cases_and_error_handling() -> None:
    """Verifies edge cases including infinities, zero division, and subnormals."""
    with pytest.raises(ValueError):
        quantize_element(1.0, scale=0.0, zero_point=0)

    with pytest.raises(ValueError):
        config = RequantConfig(0.0, 0, 1.0, 0)
        requantize_element(1, config)

    assert quantize_element(float("-inf"), 1.0, 0, DataType.UINT8) == 0
    assert quantize_element(float("inf"), 1.0, 0, DataType.UINT8) == 255
    assert quantize_element(float("nan"), 1.0, 0, DataType.UINT8) == 0
    assert quantize_element(-0.0, 1.0, 0, DataType.UINT8) == 0


def test_cpp_source_integrity() -> None:
    """Verifies that C++ source files contain required saturation and factory fixes."""
    repo_root = Path(__file__).resolve().parent.parent
    expected_files = {
        "wh": (
            "include/tt_metal/hw/ckernels/wormhole_b0/metal/llk_api/llk_sfpu/ckernel_sfpu_quant.h"
        ),
        "bh": (
            "include/tt_metal/hw/ckernels/blackhole/metal/llk_api/llk_sfpu/ckernel_sfpu_quant.h"
        ),
        "compute": "include/tt_metal/hw/inc/api/compute/quantization.h",
        "factory": (
            "include/ttnn/cpp/ttnn/operations/eltwise/binary_ng/device/"
            "binary_ng_program_factory.cpp"
        ),
        "composite": (
            "include/ttnn/cpp/ttnn/operations/eltwise/quantization/quantization.cpp"
        ),
    }
    contents = {}
    for key, rel_path in expected_files.items():
        file_path = repo_root / rel_path
        assert file_path.exists()
        contents[key] = file_path.read_text(encoding="utf-8")

    assert "_uint8_clamp_negatives_" in contents["wh"]
    assert "_uint8_round_" in contents["wh"]
    assert "QUANT_REPLAY_LEN_UINT8_OUT = 6" in contents["wh"]
    assert "REQUANT_REPLAY_LEN_UINT8_OUT = 7" in contents["wh"]

    assert "_uint8_clamp_negatives_" in contents["bh"]
    assert "_uint8_round_" in contents["bh"]
    assert "QUANT_REPLAY_LEN_UINT8_OUT = 5" in contents["bh"]

    assert "quant_uint8_tile" in contents["compute"]
    assert "requant_uint8_tile" in contents["compute"]

    assert 'set_sfpu_op("quant_uint8_tile_init", "quant_uint8_tile");' in contents["factory"]
    assert "is_narrow_quantized_dtype(c_dtype)" in contents["composite"]
