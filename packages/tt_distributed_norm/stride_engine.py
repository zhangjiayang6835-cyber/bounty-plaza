"""2D core-grid row-stride simulation and verification engine."""

from typing import Dict, List, Tuple
from packages.tt_distributed_norm.models import (
    CoreGrid2D,
    KernelStrideConfig,
    TensorShape,
    TileReadPlan,
)


def derive_2d_core_grid(
    shape: TensorShape,
    grid_size_x: int = 8,
    grid_size_y: int = 8,
) -> CoreGrid2D:
    """Calculate 2D core grid allocation and tile division factors."""
    num_tile_rows = shape.num_tile_rows
    tile_cols = shape.num_tile_cols

    cores_x = min(grid_size_y, num_tile_rows)
    while num_tile_rows % cores_x != 0 and cores_x > 1:
        cores_x -= 1
    tiles_per_core_x = num_tile_rows // cores_x

    cores_y = min(grid_size_y, tile_cols)
    while tile_cols % cores_y != 0 and cores_y > 1:
        cores_y -= 1
    tiles_per_core_y = tile_cols // cores_y

    return CoreGrid2D(
        grid_size_x=grid_size_x,
        grid_size_y=grid_size_y,
        cores_x=cores_x,
        cores_y=cores_y,
        tiles_per_core_x=tiles_per_core_x,
        tiles_per_core_y=tiles_per_core_y,
    )


def compute_core_base_offset(
    core_x: int,
    core_y: int,
    grid: CoreGrid2D,
    wt_full: int,
    defective: bool = False,
) -> int:
    """Compute base tile offset for a designated core coordinate."""
    if defective:
        return (core_x * wt_full) + (core_y * grid.tiles_per_core_y)
    row_start_index = core_x * grid.tiles_per_core_x
    return (row_start_index * wt_full) + (core_y * grid.tiles_per_core_y)


def compute_stats_offset(
    core_x: int,
    grid: CoreGrid2D,
    stats_cols: int,
    defective: bool = False,
) -> int:
    """Compute base tile offset for stats input."""
    if defective:
        return core_x * stats_cols
    return core_x * grid.tiles_per_core_x * stats_cols


def build_kernel_stride_config(
    core_x: int,
    core_y: int,
    grid: CoreGrid2D,
    shape: TensorShape,
    stats_cols: int = 1,
    defective: bool = False,
) -> KernelStrideConfig:
    """Build kernel runtime arguments representing stride and offsets."""
    wt_full = shape.num_tile_cols
    tile_offset = compute_core_base_offset(core_x, core_y, grid, wt_full, defective=defective)
    stats_offset = compute_stats_offset(core_x, grid, stats_cols, defective=defective)
    global_row_stride = 0 if defective else (wt_full - grid.tiles_per_core_y)

    return KernelStrideConfig(
        ncht=grid.tiles_per_core_x,
        wt=grid.tiles_per_core_y,
        tile_offset=tile_offset,
        global_row_stride=global_row_stride,
        stats_tile_offset=stats_offset,
        stats_tiles_cols=stats_cols,
        y_offset=core_y * grid.tiles_per_core_y,
        block_size=1,
    )


def get_ground_truth_coordinates(
    core_x: int,
    core_y: int,
    grid: CoreGrid2D,
    shape: TensorShape,
) -> List[Tuple[int, int]]:
    """Determine expected 2D tile coordinates belonging to target core."""
    coords: List[Tuple[int, int]] = []
    base_row = core_x * grid.tiles_per_core_x
    base_col = core_y * grid.tiles_per_core_y

    for r_idx in range(grid.tiles_per_core_x):
        for c_idx in range(grid.tiles_per_core_y):
            row = base_row + r_idx
            col = base_col + c_idx
            if row < shape.num_tile_rows and col < shape.num_tile_cols:
                coords.append((row, col))
    return coords


def get_ground_truth_tile_ids(
    core_x: int,
    core_y: int,
    grid: CoreGrid2D,
    shape: TensorShape,
) -> List[int]:
    """Determine expected physical 1D DRAM page IDs for target core."""
    coords = get_ground_truth_coordinates(core_x, core_y, grid, shape)
    wt_full = shape.num_tile_cols
    return [r * wt_full + c for r, c in coords]


def simulate_reader_traversal(
    core_x: int,
    core_y: int,
    grid: CoreGrid2D,
    shape: TensorShape,
    defective: bool = False,
) -> TileReadPlan:
    """Simulate exact tile index sequence read by reader kernel into local L1."""
    wt_full = shape.num_tile_cols
    base_offset = compute_core_base_offset(core_x, core_y, grid, wt_full, defective=defective)

    plan = TileReadPlan(
        core_x=core_x,
        core_y=core_y,
        base_tile_offset=base_offset,
        tiles_per_core_x=grid.tiles_per_core_x,
        tiles_per_core_y=grid.tiles_per_core_y,
        global_row_stride=0 if defective else (wt_full - grid.tiles_per_core_y),
    )

    current_idx = base_offset
    for _ in range(grid.tiles_per_core_x):
        for _ in range(grid.tiles_per_core_y):
            plan.tile_indices.append(current_idx)
            row = current_idx // wt_full
            col = current_idx % wt_full
            plan.coordinate_pairs.append((row, col))
            current_idx += 1
        if not defective:
            current_idx += (wt_full - grid.tiles_per_core_y)

    return plan


def analyze_traversal_accuracy(
    plan: TileReadPlan,
    shape: TensorShape,
) -> Dict[str, object]:
    """Inspect simulated traversal plan against mathematical ground truth."""
    grid = CoreGrid2D(
        grid_size_x=8,
        grid_size_y=8,
        cores_x=1,
        cores_y=1,
        tiles_per_core_x=plan.tiles_per_core_x,
        tiles_per_core_y=plan.tiles_per_core_y,
    )
    expected_ids = get_ground_truth_tile_ids(plan.core_x, plan.core_y, grid, shape)
    actual_ids = plan.tile_indices

    mismatch_indices: List[int] = []
    for idx, (exp, act) in enumerate(zip(expected_ids, actual_ids)):
        if exp != act:
            mismatch_indices.append(idx)

    is_accurate = len(mismatch_indices) == 0 and len(expected_ids) == len(actual_ids)
    first_corrupted = mismatch_indices[0] if mismatch_indices else -1

    return {
        "is_accurate": is_accurate,
        "mismatches_count": len(mismatch_indices),
        "first_corrupted_step": first_corrupted,
        "expected_count": len(expected_ids),
        "actual_count": len(actual_ids),
    }


def verify_grid_coverage(
    shape: TensorShape,
    grid: CoreGrid2D,
    defective: bool = False,
) -> Dict[str, object]:
    """Verify collective DRAM tile coverage across entire 2D compute mesh."""
    total_tiles = shape.total_tiles
    seen_counts: Dict[int, int] = {idx: 0 for idx in range(total_tiles)}
    out_of_bounds: List[int] = []

    for c_x in range(grid.cores_x):
        for c_y in range(grid.cores_y):
            plan = simulate_reader_traversal(c_x, c_y, grid, shape, defective=defective)
            for tile_id in plan.tile_indices:
                if 0 <= tile_id < total_tiles:
                    seen_counts[tile_id] += 1
                else:
                    out_of_bounds.append(tile_id)

    unvisited = [tid for tid, count in seen_counts.items() if count == 0]
    duplicates = [tid for tid, count in seen_counts.items() if count > 1]
    is_valid = len(unvisited) == 0 and len(duplicates) == 0 and len(out_of_bounds) == 0

    return {
        "is_valid": is_valid,
        "unvisited_count": len(unvisited),
        "duplicate_count": len(duplicates),
        "out_of_bounds_count": len(out_of_bounds),
        "total_tiles": total_tiles,
    }
