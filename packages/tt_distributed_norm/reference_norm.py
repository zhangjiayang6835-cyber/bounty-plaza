"""Reference normalization mathematics and Pearson Correlation evaluation."""

import math
from typing import List, Optional, Tuple
from packages.tt_distributed_norm.models import (
    LayerNormType,
    TensorShape,
)
from packages.tt_distributed_norm.stride_engine import (
    derive_2d_core_grid,
    simulate_reader_traversal,
)


def calculate_pearson_correlation(
    vector_a: List[float],
    vector_b: List[float],
) -> float:
    """Calculate Pearson Correlation Coefficient between two vectors."""
    if len(vector_a) != len(vector_b) or not vector_a:
        return 0.0

    length = len(vector_a)
    mean_a = sum(vector_a) / length
    mean_b = sum(vector_b) / length

    diff_a = [x - mean_a for x in vector_a]
    diff_b = [y - mean_b for y in vector_b]

    covariance = sum(da * db for da, db in zip(diff_a, diff_b))
    var_a = sum(da * da for da in diff_a)
    var_b = sum(db * db for db in diff_b)

    denominator = math.sqrt(var_a * var_b)
    if denominator == 0.0:
        return 1.0 if diff_a == diff_b else 0.0

    return max(-1.0, min(1.0, covariance / denominator))


def compute_reference_rmsnorm_row(
    row: List[float],
    weight: Optional[List[float]] = None,
    eps: float = 1e-5,
) -> List[float]:
    """Compute mathematical reference RMSNorm for a single row vector."""
    width = len(row)
    if width == 0:
        return []

    sum_sq = sum(val * val for val in row)
    rms = math.sqrt((sum_sq / width) + eps)

    if weight is not None:
        return [(val / rms) * w for val, w in zip(row, weight)]
    return [val / rms for val in row]


def compute_reference_layernorm_row(
    row: List[float],
    gamma: Optional[List[float]] = None,
    beta: Optional[List[float]] = None,
    eps: float = 1e-5,
) -> List[float]:
    """Compute mathematical reference LayerNorm for a single row vector."""
    width = len(row)
    if width == 0:
        return []

    mean = sum(row) / width
    var = sum((val - mean) ** 2 for val in row) / width
    inv_std = 1.0 / math.sqrt(var + eps)

    normalized: List[float] = []
    for idx, val in enumerate(row):
        norm_val = (val - mean) * inv_std
        if gamma is not None:
            norm_val *= gamma[idx]
        if beta is not None:
            norm_val += beta[idx]
        normalized.append(norm_val)

    return normalized


def generate_structured_matrix(shape: TensorShape) -> List[List[float]]:
    """Generate structured test matrix where elements encode row and tile identity."""
    matrix: List[List[float]] = []
    num_rows = shape.total_rows
    width = shape.width

    for r_idx in range(num_rows):
        row_vec: List[float] = []
        for c_idx in range(width):
            tile_r = r_idx // shape.tile_height
            tile_c = c_idx // shape.tile_width
            element_val = float((tile_r * 100) + (tile_c * 10) + ((r_idx + c_idx) % 7) + 1.0)
            row_vec.append(element_val)
        matrix.append(row_vec)

    return matrix


def _copy_tile_slice(
    flat_sim: List[float],
    norm_matrix: List[List[float]],
    tgt_r: int,
    tgt_c: int,
    src_r: int,
    src_c: int,
    shape: TensorShape,
) -> None:
    """Copy elements of a single tile face into the flattened simulation array."""
    tile_h = shape.tile_height
    tile_w = shape.tile_width
    width = shape.width

    for sub_r in range(tile_h):
        g_tgt_r = tgt_r * tile_h + sub_r
        g_src_r = src_r * tile_h + sub_r
        if g_src_r < len(norm_matrix):
            norm_row = norm_matrix[g_src_r]
            row_offset = g_tgt_r * width
            for sub_c in range(tile_w):
                g_tgt_c = tgt_c * tile_w + sub_c
                g_src_c = src_c * tile_w + sub_c
                if g_src_c < len(norm_row):
                    flat_sim[row_offset + g_tgt_c] = norm_row[g_src_c]


class ReferenceNormEngine:
    """Simulation engine modeling hardware tile consumption versus mathematical reference."""

    def __init__(self, shape: TensorShape, norm_type: LayerNormType = LayerNormType.RMSNORM):
        """Initialize engine with tensor geometry and normalization mode."""
        self.shape = shape
        self.norm_type = norm_type
        self.grid = derive_2d_core_grid(shape)

    def normalize_single_row(
        self,
        row: List[float],
        gamma: Optional[List[float]] = None,
        beta: Optional[List[float]] = None,
        eps: float = 1e-5,
    ) -> List[float]:
        """Apply target normalization algorithm to a single row vector."""
        if self.norm_type == LayerNormType.RMSNORM:
            return compute_reference_rmsnorm_row(row, weight=gamma, eps=eps)
        return compute_reference_layernorm_row(row, gamma=gamma, beta=beta, eps=eps)

    def run_reference(
        self,
        matrix: List[List[float]],
        gamma: Optional[List[float]] = None,
        beta: Optional[List[float]] = None,
        eps: float = 1e-5,
    ) -> List[List[float]]:
        """Compute exact non-distributed reference output."""
        return [self.normalize_single_row(r, gamma=gamma, beta=beta, eps=eps) for r in matrix]

    def _simulate_core_tile_reads(
        self,
        core_x: int,
        core_y: int,
        norm_matrix: List[List[float]],
        flat_sim: List[float],
        defective: bool,
    ) -> None:
        """Process tile sequence for an individual core."""
        wt_full = self.shape.num_tile_cols
        plan = simulate_reader_traversal(core_x, core_y, self.grid, self.shape, defective=defective)

        for step, tile_id in enumerate(plan.tile_indices):
            tgt_r = core_x * self.grid.tiles_per_core_x + (step // self.grid.tiles_per_core_y)
            tgt_c = core_y * self.grid.tiles_per_core_y + (step % self.grid.tiles_per_core_y)

            src_tile_r = tile_id // wt_full
            src_tile_c = tile_id % wt_full

            _copy_tile_slice(
                flat_sim, norm_matrix, tgt_r, tgt_c, src_tile_r, src_tile_c, self.shape
            )

    def simulate_hardware_execution(
        self,
        matrix: List[List[float]],
        defective: bool = False,
        gamma: Optional[List[float]] = None,
        beta: Optional[List[float]] = None,
        eps: float = 1e-5,
    ) -> Tuple[List[List[float]], float]:
        """Simulate hardware execution using tile reader plans and measure PCC."""
        norm_matrix = self.run_reference(matrix, gamma=gamma, beta=beta, eps=eps)
        flat_ref: List[float] = [val for row in norm_matrix for val in row]
        flat_simulated: List[float] = [0.0] * len(flat_ref)

        for c_x in range(self.grid.cores_x):
            for c_y in range(self.grid.cores_y):
                self._simulate_core_tile_reads(c_x, c_y, norm_matrix, flat_simulated, defective)

        pcc = calculate_pearson_correlation(flat_ref, flat_simulated)
        simulated_matrix: List[List[float]] = []
        width = self.shape.width
        for r_idx in range(self.shape.total_rows):
            simulated_matrix.append(flat_simulated[r_idx * width : (r_idx + 1) * width])

        return simulated_matrix, pcc
