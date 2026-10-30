// SPDX-FileCopyrightText: © 2026 Tenstorrent Inc.
// SPDX-License-Identifier: Apache-2.0
//
// writer_interleaved_fp32.cpp
// Location: ttnn/cpp/ttnn/operations/reduction/sampling/device/kernels/dataflow/writer_interleaved.cpp
//
// FIX for Issue #1836 (tt-metal#59732):
// 1. Threshold Circular Buffer (CB c_random) uses tt::DataFormat::Float32 (24-bit mantissa resolution).
// 2. Comparison against cumulative softmax probability is performed strictly in FP32 soft-float,
//    eliminating low-precision bfloat16 discretization bias and 255/256 clipping.
// 3. Reads computed data via get_read_ptr() to guarantee fresh L1 cache lines (Bug 1 fix).

#include "dataflow_api.h"
#include <cstdint>

inline float uint32_bits_to_float(uint32_t val) {
    union {
        uint32_t u;
        float f;
    } conv;
    conv.u = val;
    return conv.f;
}

inline uint32_t float_to_uint32_bits(float val) {
    union {
        float f;
        uint32_t u;
    } conv;
    conv.f = val;
    return conv.u;
}

void kernel_main() {
    uint32_t dst_addr = get_arg_val<uint32_t>(0);
    uint32_t num_users = get_arg_val<uint32_t>(1);
    uint32_t num_candidates = get_arg_val<uint32_t>(2);
    uint32_t is_top_p = get_arg_val<uint32_t>(3);

    // Circular Buffer indices
    constexpr uint32_t cb_probs_id = tt::CBIndex::c_1;     // Softmax probabilities (FP32 or widened bf16)
    constexpr uint32_t cb_indices_id = tt::CBIndex::c_8;   // Candidate token indices
    constexpr uint32_t cb_random_id = tt::CBIndex::c_24;   // Random threshold buffer (FP32 resolution)

    // Destination interleaved buffer args
    constexpr bool dst_is_dram = get_compile_time_arg_val(0) == 1;
    const InterleavedAddrGen<dst_is_dram> s = {
        .bank_base_address = dst_addr,
        .page_size = sizeof(uint32_t)
    };

    // Acquire 1 tile from each input CB
    cb_wait_front(cb_probs_id, 1);
    cb_wait_front(cb_indices_id, 1);
    cb_wait_front(cb_random_id, 1);

    // Critical: get_read_ptr() points to the valid read-side data in L1 SRAM
    volatile tt_l1_ptr float* probs_ptr = reinterpret_cast<volatile tt_l1_ptr float*>(get_read_ptr(cb_probs_id));
    volatile tt_l1_ptr uint32_t* indices_ptr = reinterpret_cast<volatile tt_l1_ptr uint32_t*>(get_read_ptr(cb_indices_id));
    volatile tt_l1_ptr float* random_ptr = reinterpret_cast<volatile tt_l1_ptr float*>(get_read_ptr(cb_random_id));

    for (uint32_t user = 0; user < num_users; ++user) {
        // High-resolution FP32 threshold in [0.0, 1.0)
        float random_threshold = random_ptr[user];

        // Soft-float cumulative summation in FP32
        float cumulative_prob = 0.0f;
        uint32_t selected_token = indices_ptr[user * num_candidates]; // fallback to first candidate

        for (uint32_t c = 0; c < num_candidates; ++c) {
            uint32_t idx = user * num_candidates + c;
            float p = probs_ptr[idx];
            cumulative_prob += p;

            // Accurate FP32 comparison against continuous threshold
            if (cumulative_prob >= random_threshold) {
                selected_token = indices_ptr[idx];
                break;
            }
        }

        // Write sampled token index to output buffer
        uint64_t dst_noc_addr = get_noc_addr(user, s);
        noc_async_write(reinterpret_cast<uint32_t>(&selected_token), dst_noc_addr, sizeof(uint32_t));
    }

    noc_async_write_barrier();

    // Release circular buffer tiles
    cb_pop_front(cb_probs_id, 1);
    cb_pop_front(cb_indices_id, 1);
    cb_pop_front(cb_random_id, 1);
}
