"""Type definitions and configuration specifications for precision kernels.

This module provides enumeration types and configuration dataclasses
for modern sqrt, rsqrt, and reciprocal operations on Tenstorrent architectures.
All legacy compatibility configurations are strictly rejected.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class PrecisionMode(str, Enum):
    """Execution precision modes for mathematical kernels."""

    APPROXIMATE = "approximate"
    PRECISE = "precise"


class DType(str, Enum):
    """Supported numeric data types."""

    BF16 = "bf16"
    FP32 = "fp32"


class Architecture(str, Enum):
    """Supported Tenstorrent hardware architectures."""

    WORMHOLE_B0 = "wormhole_b0"
    BLACKHOLE = "blackhole"
    QUASAR = "quasar"


@dataclass
class LayerNormConfig:
    """Configuration structure for LayerNorm operations.

    Legacy configuration plumbing has been eliminated.
    Passing legacy compatibility parameters explicitly raises a ValueError.
    """

    eps: float = 1e-5
    precision_mode: PrecisionMode = PrecisionMode.APPROXIMATE
    dtype: DType = DType.FP32
    legacy_reduction: bool = False
    use_welford: bool = False

    def __init__(
        self,
        eps: float = 1e-5,
        precision_mode: PrecisionMode = PrecisionMode.APPROXIMATE,
        dtype: DType = DType.FP32,
        legacy_reduction: bool = False,
        use_welford: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize LayerNorm configuration ensuring no legacy flags are present."""
        if any("legacy" in k.lower() or "compat" in k.lower() for k in kwargs):
            param_name = list(kwargs.keys())[0]
            raise ValueError(
                f"Parameter '{param_name}' is obsolete and removed. Specify precision_mode instead."
            )
        if kwargs:
            raise TypeError(f"Unrecognized keyword argument: {list(kwargs.keys())[0]}")
        self.eps = eps
        self.precision_mode = precision_mode
        self.dtype = dtype
        self.legacy_reduction = legacy_reduction
        self.use_welford = use_welford


@dataclass
class RMSNormConfig:
    """Configuration structure for RMSNorm operations."""

    eps: float = 1e-6
    precision_mode: PrecisionMode = PrecisionMode.APPROXIMATE
    dtype: DType = DType.FP32

    def __init__(
        self,
        eps: float = 1e-6,
        precision_mode: PrecisionMode = PrecisionMode.APPROXIMATE,
        dtype: DType = DType.FP32,
        **kwargs: Any,
    ) -> None:
        """Initialize RMSNorm configuration ensuring no legacy flags are present."""
        if any("legacy" in k.lower() or "compat" in k.lower() for k in kwargs):
            param_name = list(kwargs.keys())[0]
            raise ValueError(
                f"Parameter '{param_name}' is obsolete and removed. Specify precision_mode instead."
            )
        if kwargs:
            raise TypeError(f"Unrecognized keyword argument: {list(kwargs.keys())[0]}")
        self.eps = eps
        self.precision_mode = precision_mode
        self.dtype = dtype


@dataclass
class SDPAConfig:
    """Configuration structure for Scaled Dot-Product Attention kernels."""

    scale: float = 1.0
    precision_mode: PrecisionMode = PrecisionMode.PRECISE
    dtype: DType = DType.FP32
    arch: Architecture = Architecture.WORMHOLE_B0

    def __init__(
        self,
        scale: float = 1.0,
        precision_mode: PrecisionMode = PrecisionMode.PRECISE,
        dtype: DType = DType.FP32,
        arch: Architecture = Architecture.WORMHOLE_B0,
        **kwargs: Any,
    ) -> None:
        """Initialize SDPA configuration ensuring no legacy flags are present."""
        if any("legacy" in k.lower() or "compat" in k.lower() for k in kwargs):
            param_name = list(kwargs.keys())[0]
            raise ValueError(
                f"Parameter '{param_name}' is obsolete and removed. Specify precision_mode instead."
            )
        if kwargs:
            raise TypeError(f"Unrecognized keyword argument: {list(kwargs.keys())[0]}")
        self.scale = scale
        self.precision_mode = precision_mode
        self.dtype = dtype
        self.arch = arch


@dataclass
class GroupNormConfig:
    """Configuration structure for GroupNorm operations."""

    num_groups: int = 1
    eps: float = 1e-5
    precision_mode: PrecisionMode = PrecisionMode.APPROXIMATE
    dtype: DType = DType.FP32

    def __init__(
        self,
        num_groups: int = 1,
        eps: float = 1e-5,
        precision_mode: PrecisionMode = PrecisionMode.APPROXIMATE,
        dtype: DType = DType.FP32,
        **kwargs: Any,
    ) -> None:
        """Initialize GroupNorm configuration ensuring no legacy flags are present."""
        if any("legacy" in k.lower() or "compat" in k.lower() for k in kwargs):
            param_name = list(kwargs.keys())[0]
            raise ValueError(
                f"Parameter '{param_name}' is obsolete and removed. Specify precision_mode instead."
            )
        if kwargs:
            raise TypeError(f"Unrecognized keyword argument: {list(kwargs.keys())[0]}")
        self.num_groups = num_groups
        self.eps = eps
        self.precision_mode = precision_mode
        self.dtype = dtype
