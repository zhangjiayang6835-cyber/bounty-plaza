"""Type definitions and configurations for quantization operations."""

from enum import Enum, auto
from typing import NamedTuple, Union, List


class DataType(Enum):
    """Supported tensor data types for quantization operations."""

    FLOAT32 = auto()
    UINT8 = auto()
    INT8 = auto()
    INT32 = auto()


class Architecture(Enum):
    """Target hardware processor architectures."""

    WORMHOLE_B0 = auto()
    BLACKHOLE = auto()


class RequantConfig(NamedTuple):
    """Parameters defining affine input and output quantization grids."""

    in_scale: float
    in_zero_point: int
    out_scale: float
    out_zero_point: int
    dtype: DataType = DataType.UINT8


ScalarOrList = Union[
    float,
    int,
    List[float],
    List[int],
    List[List[float]],
    List[List[int]],
]
