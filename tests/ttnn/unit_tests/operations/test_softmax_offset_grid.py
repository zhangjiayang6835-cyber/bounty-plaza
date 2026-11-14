import pytest
import torch
import ttnn
from tests.ttnn.utils_for_testing import assert_with_pytorch_stats
from models.utility_functions import skip_for_grayskull

def run_softmax_offset_test(device, h, w, grid_start, grid_end, orientation, strategy, has_mask):
    # Setup grid
    core_range = ttnn.CoreRange(
        ttnn.CoreCoord(grid_start[0], grid_start[1]),
        ttnn.CoreCoord(grid_end[0], grid_end[1])
    )
    core_range_set = ttnn.CoreRangeSet({core_range})
    num_cores = (grid_end[0] - grid_start[0] + 1) * (grid_end[1] - grid_start[1] + 1)
    
    # Input tensor
    input_shape = [1, 1, h * num_cores, w]
    torch_input = torch.randn(input_shape).bfloat16()
    
    # Sharding config
    shard_spec = ttnn.ShardSpec(core_range_set, [h, w], orientation, False)
    sharded_mem_config = ttnn.MemoryConfig(ttnn.TensorMemoryLayout.HEIGHT_SHARDED, ttnn.BufferType.L1, shard_spec)
    
    # Move to device
    tt_input = ttnn.from_torch(torch_input, device=device, layout=ttnn.TILE_LAYOUT, memory_config=sharded_mem_config)
    
    # Mask setup
    tt_mask = None
    torch_mask = None
    scale = 1.0
    
    if has_mask:
        torch_mask = torch.ones([1, 1, 1, w]).bfloat16()
        tt_mask = ttnn.from_torch(torch_mask, device=device, layout=ttnn.TILE_LAYOUT)
        scale = 0.5

    # Execute
    if has_mask:
        tt_output = ttnn.scale_mask_softmax_in_place(tt_input, scale=scale, mask=tt_mask)
    else:
        tt_output = ttnn.softmax_in_place(tt_input)
    
    # Reference
    if has_mask:
        torch_output = torch.nn.functional.softmax((torch_input * scale) + torch_mask, dim=-1)
    else:
        torch_output = torch.nn.functional.softmax(torch_input, dim=-1)
    
    # Verification
    tt_output_torch = ttnn.to_torch(tt_output)
    
    # Shard-by-shard verification logic
    assert_with_pytorch_stats(torch_output, tt_output_torch)

@skip_for_grayskull("Wormhole/Blackhole specific sharding logic")
@pytest.mark.parametrize("grid_start, grid_end", [
    ((0, 0), (1, 3)), # Origin
    ((1, 0), (2, 3)), # Offset X
    ((0, 1), (1, 4)), # Offset Y
])
@pytest.mark.parametrize("orientation", [ttnn.ShardOrientation.ROW_MAJOR, ttnn.ShardOrientation.COL_MAJOR])
@pytest.mark.parametrize("has_mask", [True, False])
def test_softmax_sharded_offset_grids(device, grid_start, grid_end, orientation, has_mask):
    run_softmax_offset_test(
        device, 
        h=32, w=64, 
        grid_start=grid_start, 
        grid_end=grid_end, 
        orientation=orientation, 
        strategy=ttnn.ShardStrategy.HEIGHT,
        has_mask=has_mask
    )
