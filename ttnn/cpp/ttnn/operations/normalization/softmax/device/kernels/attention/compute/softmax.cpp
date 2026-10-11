```cpp
// SPDX-FileCopyrightText: © 2024 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "kernels/attention/softmax.hpp"
#include "kernels/data_movement.hpp"
#include "kernels/types.hpp"

namespace tt::tt_metal {

void softmax_kernel(
    uint32_t* __restrict__ input_ptr,
    uint32_t* __restrict__ output_ptr,
    uint32_t* __restrict__ mask_ptr,
    uint32_t logical_width,
    uint32_t logical_height,
    uint32_t tile_width,
    uint32_t tile_height,
    float scale,
    bool is_causal,
    bool is_in_place) {
    
    // Assume these are defined elsewhere or passed as constants
    constexpr uint32_t TILE_SIZE = 32;
    constexpr float INF = std::numeric_limits<float>::infinity();
    constexpr float NEG_INF = -std::numeric_limits<float>::infinity();

    // Local memory for processing
    alignas(64) float local_data[TILE_HEIGHT][TILE_WIDTH];
    alignas(64) float local_output[TILE_HEIGHT][TILE_WIDTH];

    // Load input data
    for (uint32_t i = 0; i < tile_height; ++i) {
        for (uint32_t j = 0; j < tile_width; ++j) {
            uint32_t idx = i * tile_width + j;
            local_data[i][j] = reinterpret_cast<float*>(input_ptr)[idx];
        }
    }

    // Apply mask if provided
    if (mask_ptr != nullptr) {
        for (uint32_t i = 0; i < tile_height; ++i) {
            for (uint32_t j = 0; j < tile_width; ++j) {
                uint32_t mask_idx = i * tile_width + j;
                uint32_t mask_val = mask_ptr[mask_idx];
                
                // For causal mask, check if j > i (assuming square matrix for simplicity in this example)
                // In reality, causal mask logic might be more complex depending on dimensions
                if (is_causal) {
                    if (j > i) { // Simplified causal check
                        local_data[i][j] = NEG_INF;
                    } else {
                        // Apply user mask if available? 
                        // Usually causal is handled separately or combined.
                        // Let's assume mask_ptr contains explicit -inf for masked positions
                        if (mask_val == 0) { // Assuming 0 means no mask, 1 means mask
                             local_data[i][j] = NEG_INF;
                        }
                    }
                } else {
                    // Broadcast mask
                    if (mask_val == 0) { // Assuming 0 means no mask, 1 means mask
                         local_data[i][j] = NEG_INF;
                    }
                }
            }
        }
    }

    // FIX: Apply padding mask for non-tile-multiple widths
    // Calculate the offset within the tile for the logical width
    uint32_t logical_width_mod = logical_width % TILE_SIZE;
    for (uint32_t i = 0; i < tile_height; ++i) {
        for (uint32_t j = logical_width_mod; j < tile_width; ++j) {
            // Only apply if logical_width is not a multiple of TILE_SIZE
            if (logical_width_mod != 0) {
                local_data[i][j] = NEG_INF;
            }
        }
    }

    // Softmax computation
    for (uint32_t i = 0; i < tile_height; ++i) {
        float max_val = -INF;
        for (uint32_t j = 0; j < tile_width; ++j) {
            if (local_data[i][j] > max_val) {
                max_val = local_data[i][j];
            }
        }

        float sum_exp = 0.0f;
        for (uint32_t j = 0; j < tile_width; ++j) {
            local_data[i][j] = expf((local_data[i][j] - max_val) * scale);
            sum_exp += local_data[i][j];
        }

        float norm = 1.0f / (sum_exp + 1e-9f); // Avoid division by zero
        for (uint32_t j = 0; j < tile_width; ++j) {
            local_output[i][j] = local_data[i][j] * norm;
        }
    }

    // Write output
    for (uint32_t i = 0; i < tile_height; ++i) {
        for (uint32_t j = 0; j < tile_width; ++j) {
            uint32_t idx = i * tile_width + j;
            reinterpret_cast<float*>(output_ptr)[idx] = local_output[i][j];
        }
    }
}

} // namespace tt::tt_metal
