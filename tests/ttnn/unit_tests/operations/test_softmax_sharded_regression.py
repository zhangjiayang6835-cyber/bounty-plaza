import pytest
import torch
import ttnn
from tests.ttnn.utils_for_testing import assert_with_pdist
from models.utility_functions import skip_for_grayskull

@skip_for_grayskull("Sharded softmax is optimized for Wormhole_B0")
@pytest.mark.parametrize("batch_size", [2])
@pytest.mark.parametrize("h, w", [(64, 128)]) # Non-square case
def test_softmax_causal_mask_sharded_wrap_logic(device, batch_size, h, w):
    torch.manual_seed(0)
    
    input_shape = [1, batch_size, h, w]
    input_data = torch.randn(input_shape).bfloat16()
    
    # Causal mask with different height than input width
    mask_shape = [1, 1, h, w]
    mask_data = torch.triu(torch.ones(mask_shape), diagonal=1) * -1e9
    
    input_tensor = ttnn.from_torch(input_data, layout=ttnn.TILE_LAYOUT, device=device, memory_config=ttnn.L1_MEMORY_CONFIG)
    mask_tensor = ttnn.from_torch(mask_data, layout=ttnn.TILE_LAYOUT, device=device, memory_config=ttnn.L1_MEMORY_CONFIG)
    
    # Sharding config
    shard_grid = ttnn.CoreRangeSet({ttnn.CoreRange(ttnn.CoreCoord(0, 0), ttnn.CoreCoord(0, 1))})
    shard_spec = ttnn.ShardSpec(shard_grid, [h // 1, w // 2], ttnn.ShardOrientation.ROW_MAJOR, False)
    sharded_mem_config = ttnn.MemoryConfig(ttnn.TensorMemoryLayout.HEIGHT_SHARDED, ttnn.BufferType.L1, shard_spec)
    
    input_tensor = ttnn.to_memory_config(input_tensor, sharded_mem_config)
    
    # Execute
    program_config = ttnn.SoftmaxShardedMultiCoreProgramConfig(
        compute_with_storage_grid_size=(1, 2),
        subblock_w=1,
        block_h=h // 32,
        block_w=w // 64,
    )
    
    output_tensor = ttnn.scale_mask_softmax_in_place(
        input_tensor,
        scale=1.0,
        mask=mask_tensor,
        program_config=program_config,
        is_causal_mask=True
    )
    
    output_data = ttnn.to_torch(output_tensor)
    
    # Reference
    ref_input = input_data + mask_data
    expected_output = torch.softmax(ref_input, dim=-1)
    
    assert_with_pdist(output_data, expected_output)

def test_softmax_sharded_invalid_orientation_rejection(device):
    h, w = 32, 64
    input_shape = [1, 1, h, w]
    input_data = torch.randn(input_shape).bfloat16()
    
    shard_grid = ttnn.CoreRangeSet({ttnn.CoreRange(ttnn.CoreCoord(0, 0), ttnn.CoreCoord(0, 0))})
    
    # Input is ROW_MAJOR sharded
    input_spec = ttnn.ShardSpec(shard_grid, [32, 64], ttnn.ShardOrientation.ROW_MAJOR, False)
    input_mem = ttnn.MemoryConfig(ttnn.TensorMemoryLayout.BLOCK_SHARDED, ttnn.BufferType.L1, input_spec)
    
    # Mask is COL_MAJOR sharded (Incompatible)
    mask_spec = ttnn.ShardSpec(shard_grid, [32, 64], ttnn.ShardOrientation.COL_MAJOR, False)
    mask_mem = ttnn.MemoryConfig(ttnn.TensorMemoryLayout.BLOCK_SHARDED, ttnn.BufferType.L1, mask_spec)
    
    input_tensor = ttnn.from_torch(input_data, layout=ttnn.TILE_LAYOUT, device=device, memory_config=input_mem)
    mask_data = torch.randn(input_shape).bfloat16()
    mask_tensor = ttnn.from_torch(mask_data, layout=ttnn.TILE_LAYOUT, device=device, memory_config=mask_mem)
    
    with pytest.raises(Exception) as e:
        ttnn.scale_mask_softmax_in_place(
            input_tensor,
            mask=mask_tensor,
            is_causal_mask=False
        )
    assert "orientation must match" in str(e.value)
