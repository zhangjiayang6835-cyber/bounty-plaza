// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
// SPDX-License-Identifier: Apache-2.0

#include "ttnn/operations/quantization/quantize/quantize.hpp"
#include "ttnn/operations/quantization/quantize/quantize_impl.hpp"
#include "tt_metal/api/util/util.hpp"
#include "tt_metal/impl/dispatch.hpp"

namespace ttnn::operations::quantization {

using namespace tt::constants;

void quantize_op(const Tensor& input, const std::optional<float>& scale, const std::optional<int32_t>& zero_point, const DataType& output_dtype) {
    // ... existing validation and setup ...
    
    // If output dtype is uint8, ensure lower bound saturation is handled by the kernel
    // The kernel itself has been updated to clamp to [0, 255]
    
    // Dispatch to kernel
    // ...
}

} // namespace ttnn::operations::quantization
