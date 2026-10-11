// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
// SPDX-License-Identifier: Apache-2.0

#include "kernel.hpp"
#include "data_format.h"
#include "quantization_utils.hpp"

namespace {

void requantize_kernel(uint32_t input_tile_id, uint32_t output_tile_id, 
                       uint32_t input_scale, uint32_t input_zero_point, 
                       uint32_t output_scale, uint32_t output_zero_point) {
    // ... existing setup code ...
    
    // Read input tile
    // ...
    
    // Process each element
    for (int i = 0; i < TILE_SIZE; ++i) {
        int32_t input_val = read_input(i);
        
        // Calculate requantized value:
        // out = clamp(round((input - input_zero_point) * input_scale / output_scale + output_zero_point), 0, 255)
        
        int32_t requantized_val = round_requantize(input_val, input_zero_point, input_scale, output_scale, output_zero_point);
        
        // FIX: Clamp to [0, 255] for uint8
        if (requantized_val < 0) {
            requantized_val = 0;
        } else if (requantized_val > 255) {
            requantized_val = 255;
        }
        
        write_output(i, static_cast<uint8_t>(requantized_val));
    }
}

} // namespace

extern "C" {
    void main() {
        // ... entry point ...
    }
}
