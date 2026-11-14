#include <algorithm>

#include "ttnn/operations/normalization/softmax/device/softmax_op.hpp"
#include "tt_metal/host_api.hpp"
#include "tt_metal/common/constants.hpp"
#include "tt_metal/detail/util.hpp"

namespace tt {
namespace tt_metal {

operation::ProgramWithRuntimeArgs softmax_sharded_multi_core(
    const Tensor &input,
    const Tensor &output,
    const std::optional<const Tensor> mask,
    float scale,
    bool causal_mask,
    CoreRangeSet all_cores,
    bool in_place
) {
    Program program = CreateProgram();

    Device *device = input.device();
    auto shard_spec = input.shard_spec().value();
    auto shard_grid = shard_spec.grid;
    auto shard_orientation = shard_spec.orientation;
    
    uint32_t num_cores = all_cores.num_cores();
    
    // Kernel and Buffer setup (Simplified for brevity, focusing on the fix)
    // ... (Existing Circular Buffer and Kernel definitions) ...

    // THE FIX: Instead of calculating core coordinates based on a linear index 0..N,
    // we must iterate through the CoreRangeSet to respect the offset grid.
    
    auto all_cores_vec = grid_to_cores(num_cores, shard_grid, shard_orientation);

    for (uint32_t i = 0; i < num_cores; ++i) {
        CoreCoord core = all_cores_vec[i]; // Correctly retrieves the physical core even if offset

        // Set runtime args for the reader/writer/compute kernels
        // Ensure that the shard index 'i' is associated with the correct physical 'core'
        std::vector<uint32_t> reader_args = { i, scale_int }; 
        tt_metal::SetRuntimeArgs(program, reader_kernel_id, core, reader_args);
        tt_metal::SetRuntimeArgs(program, writer_kernel_id, core, { i });
    }

    return {std::move(program)};
}

}  // namespace tt_metal
}  // namespace tt
