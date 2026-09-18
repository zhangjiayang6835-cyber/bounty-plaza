"""Data models and hardware specifications for distributed normalization."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple


class LayerNormType(Enum):
    """Supported distributed normalization types."""

    LAYERNORM = "layernorm"
    RMSNORM = "rmsnorm"


class NormPhase(Enum):
    """Phases of distributed normalization execution."""

    PRE_ALLGATHER = "pre_allgather"
    POST_ALLGATHER = "post_allgather"
    POST_ALLGATHER_WELFORD = "post_allgather_welford"


@dataclass(frozen=True)
class TensorShape:
    """Tensor geometric dimensions and tiling properties."""

    batch: int
    channels: int
    height: int
    width: int
    tile_height: int = 32
    tile_width: int = 32

    @property
    def total_rows(self) -> int:
        """Calculate total rows in tensor."""
        return self.batch * self.channels * self.height

    @property
    def num_tile_rows(self) -> int:
        """Calculate total row count measured in tiles."""
        return (self.batch * self.channels * self.height) // self.tile_height

    @property
    def num_tile_cols(self) -> int:
        """Calculate total column count measured in tiles."""
        return self.width // self.tile_width

    @property
    def total_tiles(self) -> int:
        """Calculate total tile volume across the tensor."""
        return self.num_tile_rows * self.num_tile_cols


@dataclass(frozen=True)
class CoreGrid2D:
    """Hardware compute core grid topology and work distribution."""

    grid_size_x: int
    grid_size_y: int
    cores_x: int
    cores_y: int
    tiles_per_core_x: int
    tiles_per_core_y: int

    @property
    def total_allocated_cores(self) -> int:
        """Calculate total cores participating in 2D compute."""
        return self.cores_x * self.cores_y

    @property
    def is_multi_row_per_core(self) -> bool:
        """Check if any core manages more than a single row tile."""
        return self.tiles_per_core_x > 1


@dataclass
class TileReadPlan:
    """Plan specifying the ordered sequence of physical DRAM tiles read by a core."""

    core_x: int
    core_y: int
    base_tile_offset: int
    tiles_per_core_x: int
    tiles_per_core_y: int
    global_row_stride: int
    tile_indices: List[int] = field(default_factory=list)
    coordinate_pairs: List[Tuple[int, int]] = field(default_factory=list)

    @property
    def count(self) -> int:
        """Return number of tiles planned for reading."""
        return len(self.tile_indices)


@dataclass
class KernelStrideConfig:
    """Stride arguments and boundary condition parameters for reader kernels."""

    ncht: int
    wt: int
    tile_offset: int
    global_row_stride: int
    stats_tile_offset: int = 0
    stats_tiles_cols: int = 1
    y_offset: int = 0
    block_size: int = 1
