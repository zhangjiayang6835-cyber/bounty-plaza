"""Universal tt-metal distributed normalization library."""

from packages.tt_distributed_norm.c_kernels import CppPatchGenerator
from packages.tt_distributed_norm.models import (
    CoreGrid2D,
    KernelStrideConfig,
    LayerNormType,
    NormPhase,
    TensorShape,
    TileReadPlan,
)
from packages.tt_distributed_norm.reference_norm import (
    ReferenceNormEngine,
    calculate_pearson_correlation,
    compute_reference_layernorm_row,
    compute_reference_rmsnorm_row,
    generate_structured_matrix,
)
from packages.tt_distributed_norm.settlement import (
    BountySettlementEngine,
    validate_evm_address,
    validate_stellar_address,
)
from packages.tt_distributed_norm.stride_engine import (
    analyze_traversal_accuracy,
    build_kernel_stride_config,
    compute_core_base_offset,
    compute_stats_offset,
    derive_2d_core_grid,
    get_ground_truth_coordinates,
    get_ground_truth_tile_ids,
    simulate_reader_traversal,
    verify_grid_coverage,
)

__all__ = [
    "CppPatchGenerator",
    "CoreGrid2D",
    "KernelStrideConfig",
    "LayerNormType",
    "NormPhase",
    "TensorShape",
    "TileReadPlan",
    "ReferenceNormEngine",
    "calculate_pearson_correlation",
    "compute_reference_layernorm_row",
    "compute_reference_rmsnorm_row",
    "generate_structured_matrix",
    "BountySettlementEngine",
    "validate_evm_address",
    "validate_stellar_address",
    "analyze_traversal_accuracy",
    "build_kernel_stride_config",
    "compute_core_base_offset",
    "compute_stats_offset",
    "derive_2d_core_grid",
    "get_ground_truth_coordinates",
    "get_ground_truth_tile_ids",
    "simulate_reader_traversal",
    "verify_grid_coverage",
]
