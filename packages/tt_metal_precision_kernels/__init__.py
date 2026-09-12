"""Universal Tenstorrent Precision Kernels without legacy plumbing.

This package provides canonical mathematical kernels, normalization routines,
attention primitives, and model configuration validators for Tenstorrent hardware,
adhering strictly to modern numerical precision and zero legacy compatibility paths.
"""

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
    ModelConfiguration,
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

__all__ = [
    "Architecture",
    "DType",
    "PrecisionMode",
    "LayerNormConfig",
    "RMSNormConfig",
    "SDPAConfig",
    "GroupNormConfig",
    "compute_reciprocal",
    "compute_sqrt",
    "compute_rsqrt",
    "quantize_bf16",
    "recip_tile",
    "sqrt_tile",
    "rsqrt_tile",
    "layer_norm",
    "rms_norm",
    "group_norm",
    "distributed_rms_norm",
    "softmax",
    "scaled_dot_product_attention",
    "sampling_recip_scalar",
    "ModelArchitecture",
    "ModelConfiguration",
    "migrate_legacy_config",
    "get_canonical_model_config",
    "scan_source_text",
    "scan_codebase_directory",
]
