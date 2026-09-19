"""Public API for tt_sfploadmacro_coverage package."""

from .models import (
    ApproximationMode,
    DataFormat,
    DestAccumulation,
    ExecutionMode,
    ReciprocalSweepSuite,
    ReciprocalVariant,
    SFPUArchitecture,
    SimulationResult,
    TileShape,
    TraceCycle,
)
from .reference_math import (
    calculate_pearson_correlation,
    compute_arecip_7b,
    compute_exact_reciprocal,
    compute_reciprocal_bf16_8b_3c,
    compute_reciprocal_fp32_24b_5c,
    generate_reciprocal_stimuli,
)
from .hazard_engine import (
    SFPUMacroSimulationEngine,
    TimingHazardDetector,
)
from .c_kernels import CppPatchGenerator
from .settlement import (
    BountyRewardCalculation,
    BountySettlementEngine,
    validate_evm_address,
    validate_stellar_address,
)

__all__ = [
    "ApproximationMode",
    "DataFormat",
    "DestAccumulation",
    "ExecutionMode",
    "ReciprocalSweepSuite",
    "ReciprocalVariant",
    "SFPUArchitecture",
    "SimulationResult",
    "TileShape",
    "TraceCycle",
    "calculate_pearson_correlation",
    "compute_arecip_7b",
    "compute_exact_reciprocal",
    "compute_reciprocal_bf16_8b_3c",
    "compute_reciprocal_fp32_24b_5c",
    "generate_reciprocal_stimuli",
    "SFPUMacroSimulationEngine",
    "TimingHazardDetector",
    "CppPatchGenerator",
    "BountyRewardCalculation",
    "BountySettlementEngine",
    "validate_evm_address",
    "validate_stellar_address",
]
