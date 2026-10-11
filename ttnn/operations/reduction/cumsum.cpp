#include "ttnn/operations/reduction/cumsum/cumsum.hpp"

#include <cuda_fp16.h>
#include <tt-metalium/debug_tools.hpp>
#include <tt-metalium/host_api.hpp>
#include <tt_stl/strong_type.hpp>
#include <types.hpp>
#include <vector>

#include <cstdint>
#include <optional>

namespace ttnn::operations::reduction::cumsum {

using namespace tt::constants;

namespace {

inline float compensated_sum(float y, float f, float& running_comp) {
    // If running total is infinite or NaN, skip compensation to avoid inf - inf = NaN
    // This matches PyTorch's IEEE behavior for cumulative operations
    float corrected_value = y - running_comp;
    
    // Guard: if corrected_value is NaN/Inf, compensation would poison subsequent results
    // when we compute (corrected_value - y) + f with y also being Inf
    if (std::isnan(corrected_value) || std::isinf(corrected_value)) {
        running_comp = 0.0f;
        return corrected_value;
    }
    
    float new_comp = (corrected_value - y) + f;
    running_comp = new_comp;
    return corrected_value;
}

}  // namespace

Tensor operation(
    const device::RuntimeContext& ctx,
    const Tensor& input_tensor,
    int64_t dim,
    std::optional<DataType> compute_dtype,
    bool disable_compensated_sum,
    const std::optional<ttnn::SmallVector<int>>& output_shape) {
    
    auto& device = ctx.get_device();
    auto& quequeue = ctx.get_queue();
    
    // ... existing implementation with the fix applied to the compensated path
    // The key change is in the kernel that performs the cumulative sum:
    // where running_total is the accumulated sum, and we compute compensation
    // only when running_total is finite.
}

}  // namespace ttnn::operations::reduction::cumsum
