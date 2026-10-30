// SPDX-FileCopyrightText: © 2026 Tenstorrent Inc.
// SPDX-License-Identifier: Apache-2.0
//
// sampling_kernel_common.hpp
// Location: ttnn/cpp/ttnn/operations/reduction/sampling/device/kernels/sampling_kernel_common.hpp
//
// Common definitions and Philox-4x32 PRNG helper functions for Tensix cores.

#pragma once

#include <cstdint>

struct Philox4x32State {
    uint32_t counter[4];
    uint32_t key[2];
};

inline void philox_round(uint32_t ctr[4], const uint32_t key[2]) {
    constexpr uint64_t PHILOX_M4x32_0 = 0xD2511F53ULL;
    constexpr uint64_t PHILOX_M4x32_1 = 0xCD9E8D57ULL;

    uint64_t prod0 = static_cast<uint64_t>(ctr[0]) * PHILOX_M4x32_0;
    uint32_t hi0 = static_cast<uint32_t>(prod0 >> 32);
    uint32_t lo0 = static_cast<uint32_t>(prod0);

    uint64_t prod1 = static_cast<uint64_t>(ctr[2]) * PHILOX_M4x32_1;
    uint32_t hi1 = static_cast<uint32_t>(prod1 >> 32);
    uint32_t lo1 = static_cast<uint32_t>(prod1);

    uint32_t out0 = hi1 ^ ctr[1] ^ key[0];
    uint32_t out1 = lo1;
    uint32_t out2 = hi0 ^ ctr[3] ^ key[1];
    uint32_t out3 = lo0;

    ctr[0] = out0;
    ctr[1] = out1;
    ctr[2] = out2;
    ctr[3] = out3;
}

inline float philox_generate_uniform_fp32(uint32_t ctr[4], uint32_t key[2]) {
    constexpr uint32_t PHILOX_W32_0 = 0x9E3779B9U;
    constexpr uint32_t PHILOX_W32_1 = 0xBB67AE85U;

    for (int r = 0; r < 10; ++r) {
        philox_round(ctr, key);
        key[0] += PHILOX_W32_0;
        key[1] += PHILOX_W32_1;
    }

    // Convert 24 most significant bits into uniform float in [0.0, 1.0)
    uint32_t u24 = (ctr[0] >> 8) & 0xFFFFFFU;
    return static_cast<float>(u24) * (1.0f / 16777216.0f);
}
