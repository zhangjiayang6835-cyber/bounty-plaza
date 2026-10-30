// SPDX-FileCopyrightText: © 2026 Tenstorrent Inc.
// SPDX-License-Identifier: Apache-2.0
//
// sampling_device_operation.cpp
// Location: ttnn/cpp/ttnn/operations/reduction/sampling/device/sampling_op.cpp
//
// Device operation implementation configuring Circular Buffers and kernels
// for Wormhole B0 and Blackhole Tensix compute engines.

#include "ttnn/operations/reduction/sampling/device/sampling_op.hpp"
#include "tt_metal/host_api.hpp"
#include "tt_metal/common/constants.hpp"

namespace ttnn::operations::reduction {

SamplingOperation::ProgramFactory::shared_variables_t SamplingOperation::ProgramFactory::override_runtime_arguments(
    Program& program,
    const operation_attributes_t& operation_attributes,
    const tensor_args_t& tensor_args,
    tensor_return_value_t& tensor_return_value) {
    // Runtime argument updates for trace replay and per-user manual seeding
    return {};
}

operation::ProgramWithCallbacks SamplingOperation::ProgramFactory::create(
    const operation_attributes_t& operation_attributes,
    const tensor_args_t& tensor_args,
    tensor_return_value_t& output) {

    Program program{};
    IDevice* device = tensor_args.input_tensor.device();
    ARCH arch = device->arch();

    TT_FATAL(
        arch == ARCH::WORMHOLE_B0 || arch == ARCH::BLACKHOLE,
        "Sampling FP32 random threshold is only supported on Wormhole B0 and Blackhole architectures."
    );

    uint32_t num_users = tensor_args.input_tensor.get_logical_shape()[0];
    uint32_t num_candidates = tensor_args.input_tensor.get_logical_shape()[-1];

    // Configure Circular Buffer for Random Threshold (CB c_24)
    // FIX: Set DataFormat to Float32 (4 bytes/element) instead of Float16_b / bfloat16
    constexpr uint32_t cb_random_id = tt::CBIndex::c_24;
    constexpr uint32_t single_tile_size_bytes = 1024 * sizeof(float); // 32x32 FP32 tile = 4096 bytes

    CircularBufferConfig cb_random_config = CircularBufferConfig(
        single_tile_size_bytes,
        {{cb_random_id, tt::DataFormat::Float32}}
    ).set_page_size(cb_random_id, single_tile_size_bytes);

    CoreCoord core_coord = {0, 0};
    CreateCircularBuffer(program, core_coord, cb_random_config);

    // Create Dataflow Writer Kernel using FP32 comparison
    std::vector<uint32_t> writer_compile_time_args = {
        static_cast<uint32_t>(output.buffer()->is_dram() ? 1 : 0)
    };

    KernelHandle writer_kernel_id = CreateKernel(
        program,
        "ttnn/cpp/ttnn/operations/reduction/sampling/device/kernels/dataflow/writer_interleaved.cpp",
        core_coord,
        DataMovementConfig{
            .processor = DataMovementProcessor::RISCV_1,
            .noc = NOC::RISCV_1_default,
            .compile_args = writer_compile_time_args
        }
    );

    SetRuntimeArgs(
        program,
        writer_kernel_id,
        core_coord,
        {
            output.buffer()->address(),
            num_users,
            num_candidates,
            static_cast<uint32_t>(operation_attributes.top_p < 1.0f ? 1 : 0)
        }
    );

    return {std::move(program)};
}

} // namespace ttnn::operations::reduction
