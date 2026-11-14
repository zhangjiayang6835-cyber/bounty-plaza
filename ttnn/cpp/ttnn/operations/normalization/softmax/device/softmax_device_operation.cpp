#include "ttnn/operations/normalization/softmax/device/softmax_op.hpp"
#include "tt_metal/host_api.hpp"
#include "tt_metal/common/constants.hpp"

namespace ttnn::operations::normalization {

void SoftmaxDeviceOperation::validate(const std::vector<Tensor>& input_tensors, const std::vector<std::optional<const Tensor>>& optional_input_tensors) const {
    const auto& input_tensor = input_tensors.at(0);
    const auto& mask = optional_input_tensors.at(0);

    TT_FATAL(input_tensor.storage_type() == StorageType::DEVICE, "Operands to softmax need to be on device!");
    TT_FATAL(input_tensor.buffer() != nullptr, "Operands to softmax need to be allocated in buffers!");
    TT_FATAL(input_tensor.get_layout() == Layout::TILE, "Softmax currently only supports tile layout.");

    if (this->program_config.index() == 1) { // SoftmaxShardedMultiCoreProgramConfig
        auto config = std::get<SoftmaxShardedMultiCoreProgramConfig>(this->program_config);
        TT_FATAL(input_tensor.is_sharded(), "Input must be sharded for ShardedMultiCoreProgramConfig");

        if (mask.has_value()) {
            const auto& mask_tensor = mask.value();
            
            // Issue 1 & 4: Shard Spec and Layout Validation
            if (this->is_causal_mask) {
                TT_FATAL(mask_tensor.get_layout() == Layout::TILE, "Causal mask must be in Tile layout to avoid device hangs in sharded mode.");
            }

            if (mask_tensor.is_sharded()) {
                const auto& input_shard_spec = input_tensor.shard_spec().value();
                const auto& mask_shard_spec = mask_tensor.shard_spec().value();
                TT_FATAL(input_shard_spec.orientation == mask_shard_spec.orientation, "Input and mask shard orientation must match.");
                TT_FATAL(input_shard_spec.num_cores() == mask_shard_spec.num_cores(), "Input and mask must be sharded across the same number of cores.");
            }
        }
    }
}

// ... rest of the implementation remains the same
} // namespace ttnn::operations::normalization
