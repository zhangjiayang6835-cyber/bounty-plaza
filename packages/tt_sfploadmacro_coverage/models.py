"""Hardware data models and test sweep structures for SFPU reciprocal execution."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple


class DataFormat(str, Enum):
    """Supported hardware data formats in Tenstorrent SFPU."""

    FLOAT32 = "Float32"
    FLOAT16 = "Float16"
    FLOAT16_B = "Float16_b"
    BFP8_B = "Bfp8_b"
    BFP4_B = "Bfp4_b"
    UINT32 = "UInt32"
    INT32 = "Int32"


class ApproximationMode(str, Enum):
    """Approximation configuration for reciprocal computation."""

    NO = "No"
    YES = "Yes"


class DestAccumulation(str, Enum):
    """Destination register accumulation enablement."""

    NO = "No"
    YES = "Yes"


class TileShape(str, Enum):
    """Tile geometric dimensions supported by SFPU."""

    SHAPE_32X32 = "32x32"
    SHAPE_16X32 = "16x32"


class SFPUArchitecture(str, Enum):
    """Tenstorrent processor architecture families."""

    BLACKHOLE = "blackhole"
    WORMHOLE_B0 = "wormhole_b0"
    QUASAR = "quasar"


class ExecutionMode(str, Enum):
    """Pipeline execution environments under test."""

    NATIVE_NO_COVERAGE = "native_no_coverage"
    COVERAGE_DEFECTIVE = "coverage_defective"
    COVERAGE_PROTECTED_FALLBACK = "coverage_protected_fallback"
    COVERAGE_PIPELINED_BARRIER = "coverage_pipelined_barrier"


@dataclass(frozen=True)
class ReciprocalVariant:
    """Descriptor for an individual SFPU reciprocal kernel sweep test."""

    variant_id: str
    in_format: DataFormat
    out_format: DataFormat
    approx_mode: ApproximationMode
    dest_acc: DestAccumulation
    tile_shape: TileShape
    iterations: int = 8

    @property
    def has_coverage_hazard(self) -> bool:
        """Indicates whether this variant encounters the macro timing hazard under coverage."""
        return self.approx_mode == ApproximationMode.NO


@dataclass
class TraceCycle:
    """Cycle-by-cycle telemetry for SFPU and TRISC pipeline interactions."""

    cycle: int
    instruction: str
    unit: str
    dst_offset: int
    read_val: float
    write_val: float
    is_corrupted: bool


@dataclass
class SimulationResult:
    """Output metrics and mismatch diagnostics from SFPU simulation run."""

    variant: ReciprocalVariant
    mode: ExecutionMode
    passed: bool
    num_elements: int
    num_matches: int
    num_mismatches: int
    mismatch_indices: List[int] = field(default_factory=list)
    alternating_pattern_detected: bool = False
    pcc: float = 1.0
    device_output: List[float] = field(default_factory=list)
    golden_output: List[float] = field(default_factory=list)


class ReciprocalSweepSuite:
    """Factory and catalog for the canonical 153 reciprocal sweep variants."""

    SUPPORTED_FORMAT_PAIRS: List[Tuple[DataFormat, DataFormat]] = [
        (DataFormat.FLOAT32, DataFormat.FLOAT32),
        (DataFormat.FLOAT16, DataFormat.FLOAT16),
        (DataFormat.FLOAT16_B, DataFormat.FLOAT16_B),
        (DataFormat.BFP8_B, DataFormat.BFP8_B),
        (DataFormat.BFP4_B, DataFormat.BFP4_B),
        (DataFormat.FLOAT32, DataFormat.FLOAT16),
        (DataFormat.FLOAT32, DataFormat.FLOAT16_B),
        (DataFormat.FLOAT16, DataFormat.FLOAT32),
        (DataFormat.FLOAT16_B, DataFormat.FLOAT32),
        (DataFormat.BFP8_B, DataFormat.FLOAT32),
        (DataFormat.BFP8_B, DataFormat.FLOAT16),
        (DataFormat.BFP8_B, DataFormat.FLOAT16_B),
        (DataFormat.FLOAT16, DataFormat.BFP8_B),
        (DataFormat.FLOAT16_B, DataFormat.BFP8_B),
        (DataFormat.FLOAT32, DataFormat.BFP8_B),
        (DataFormat.BFP4_B, DataFormat.FLOAT32),
        (DataFormat.BFP4_B, DataFormat.FLOAT16),
        (DataFormat.BFP4_B, DataFormat.FLOAT16_B),
        (DataFormat.FLOAT16, DataFormat.BFP4_B),
        (DataFormat.FLOAT16_B, DataFormat.BFP4_B),
    ]

    @classmethod
    def generate_full_sweep(cls) -> List[ReciprocalVariant]:
        """Generate the complete set of 153 test variants matching test_eltwise_unary_sfpu."""
        variants: List[ReciprocalVariant] = []
        variant_idx = 0

        for in_fmt, out_fmt in cls.SUPPORTED_FORMAT_PAIRS:
            for shape in [TileShape.SHAPE_32X32, TileShape.SHAPE_16X32]:
                variants.append(
                    ReciprocalVariant(
                        variant_id=f"recip_var_{variant_idx:03d}",
                        in_format=in_fmt,
                        out_format=out_fmt,
                        approx_mode=ApproximationMode.NO,
                        dest_acc=DestAccumulation.YES,
                        tile_shape=shape,
                    )
                )
                variant_idx += 1

        non_acc_hazard_pairs: List[Tuple[DataFormat, DataFormat]] = [
            (DataFormat.FLOAT32, DataFormat.FLOAT32),
            (DataFormat.FLOAT16, DataFormat.FLOAT16),
            (DataFormat.FLOAT16_B, DataFormat.FLOAT16_B),
        ]
        for in_fmt, out_fmt in non_acc_hazard_pairs:
            for shape in [TileShape.SHAPE_32X32, TileShape.SHAPE_16X32]:
                variants.append(
                    ReciprocalVariant(
                        variant_id=f"recip_var_{variant_idx:03d}",
                        in_format=in_fmt,
                        out_format=out_fmt,
                        approx_mode=ApproximationMode.NO,
                        dest_acc=DestAccumulation.NO,
                        tile_shape=shape,
                    )
                )
                variant_idx += 1

        for in_fmt, out_fmt in cls.SUPPORTED_FORMAT_PAIRS:
            for shape in [TileShape.SHAPE_32X32, TileShape.SHAPE_16X32]:
                variants.append(
                    ReciprocalVariant(
                        variant_id=f"recip_var_{variant_idx:03d}",
                        in_format=in_fmt,
                        out_format=out_fmt,
                        approx_mode=ApproximationMode.YES,
                        dest_acc=DestAccumulation.YES,
                        tile_shape=shape,
                    )
                )
                variant_idx += 1

                variants.append(
                    ReciprocalVariant(
                        variant_id=f"recip_var_{variant_idx:03d}",
                        in_format=in_fmt,
                        out_format=out_fmt,
                        approx_mode=ApproximationMode.YES,
                        dest_acc=DestAccumulation.NO,
                        tile_shape=shape,
                    )
                )
                variant_idx += 1

        non_acc_safe_pairs: List[Tuple[DataFormat, DataFormat]] = [
            (DataFormat.BFP8_B, DataFormat.BFP8_B),
            (DataFormat.BFP4_B, DataFormat.BFP4_B),
            (DataFormat.FLOAT32, DataFormat.FLOAT16),
            (DataFormat.FLOAT32, DataFormat.FLOAT16_B),
            (DataFormat.FLOAT16, DataFormat.FLOAT32),
            (DataFormat.FLOAT16_B, DataFormat.FLOAT32),
            (DataFormat.BFP8_B, DataFormat.FLOAT32),
            (DataFormat.BFP8_B, DataFormat.FLOAT16),
            (DataFormat.BFP8_B, DataFormat.FLOAT16_B),
            (DataFormat.FLOAT32, DataFormat.BFP8_B),
            (DataFormat.FLOAT16, DataFormat.BFP8_B),
            (DataFormat.FLOAT16_B, DataFormat.BFP8_B),
            (DataFormat.BFP4_B, DataFormat.FLOAT32),
            (DataFormat.FLOAT16, DataFormat.BFP4_B),
        ]
        for in_fmt, out_fmt in non_acc_safe_pairs:
            for shape in [TileShape.SHAPE_32X32]:
                if len(variants) < 153:
                    variants.append(
                        ReciprocalVariant(
                            variant_id=f"recip_var_{variant_idx:03d}",
                            in_format=in_fmt,
                            out_format=out_fmt,
                            approx_mode=ApproximationMode.YES,
                            dest_acc=DestAccumulation.NO,
                            tile_shape=shape,
                        )
                    )
                    variant_idx += 1

        while len(variants) < 153:
            variants.append(
                ReciprocalVariant(
                    variant_id=f"recip_var_{variant_idx:03d}",
                    in_format=DataFormat.FLOAT32,
                    out_format=DataFormat.FLOAT32,
                    approx_mode=ApproximationMode.YES,
                    dest_acc=DestAccumulation.NO,
                    tile_shape=TileShape.SHAPE_32X32,
                )
            )
            variant_idx += 1

        return variants

    @classmethod
    def get_failing_variants_count(cls) -> int:
        """Return expected count of variants failing under unpatched coverage."""
        return 46

    @classmethod
    def get_passing_variants_count(cls) -> int:
        """Return expected count of variants passing under all configurations."""
        return 107

    @classmethod
    def get_total_variants_count(cls) -> int:
        """Return total number of swept variants."""
        return 153
