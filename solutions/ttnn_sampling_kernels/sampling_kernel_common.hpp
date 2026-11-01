// SPDX-FileCopyrightText: © 2026 Tenstorrent Inc.
// SPDX-License-Identifier: Apache-2.0
// Fix for TT-Metal Issue #59732: Full FP32 Random Threshold for Sampling

#pragma once

#include <cstdint>

namespace ttnn::operations::reduction::sampling {

struct SamplingConfig {
    uint32_t top_k;
    float top_p;
    float temperature;
    uint32_t seed;
    bool use_fp32_threshold;
};

// FP32 random threshold circular buffer definition
// Replaces legacy 2-byte Float16_b with 4-byte Float32
constexpr uint32_t CB_RANDOM_THRESHOLD_INDEX = 24;
constexpr uint32_t FP32_BYTES_PER_ELEMENT = 4;

inline float generate_fp32_random_uniform(uint32_t& prng_state) {
    // 32-bit linear congruential generator / xorshift32
    prng_state ^= (prng_state << 13);
    prng_state ^= (prng_state >> 17);
    prng_state ^= (prng_state << 5);
    // Convert 24 significant bits to uniform float [0, 1.0)
    constexpr float INV_2_POW_24 = 1.0f / 16777216.0f;
    return static_cast<float>(prng_state & 0x00FFFFFF) * INV_2_POW_24;
}

} // namespace ttnn::operations::reduction::sampling
