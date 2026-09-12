"""Quantization kernels and saturation verification suite."""

from packages.ttnn_quantize_saturation.types import (
    DataType,
    Architecture,
    RequantConfig,
)
from packages.ttnn_quantize_saturation.kernels import (
    quantize,
    requantize,
    dequantize,
    quantize_element,
    requantize_element,
    dequantize_element,
)
from packages.ttnn_quantize_saturation.composite import (
    narrow_composite_result,
    is_narrow_quantized_dtype,
)
from packages.ttnn_quantize_saturation.sfpu_emulator import (
    SFPUSimulator,
    SFPURegisterState,
    WH_QUANT_REPLAY_LEN_UINT8_OUT,
    WH_REQUANT_REPLAY_LEN_UINT8_OUT,
    BH_QUANT_REPLAY_LEN_UINT8_OUT,
    BH_REQUANT_REPLAY_LEN_UINT8_2S_COMP,
    BH_REQUANT_REPLAY_LEN_UINT8_SIGN_MAGN,
)

__all__ = [
    "DataType",
    "Architecture",
    "RequantConfig",
    "quantize",
    "requantize",
    "dequantize",
    "quantize_element",
    "requantize_element",
    "dequantize_element",
    "narrow_composite_result",
    "is_narrow_quantized_dtype",
    "SFPUSimulator",
    "SFPURegisterState",
    "WH_QUANT_REPLAY_LEN_UINT8_OUT",
    "WH_REQUANT_REPLAY_LEN_UINT8_OUT",
    "BH_QUANT_REPLAY_LEN_UINT8_OUT",
    "BH_REQUANT_REPLAY_LEN_UINT8_2S_COMP",
    "BH_REQUANT_REPLAY_LEN_UINT8_SIGN_MAGN",
]
