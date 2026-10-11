// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
// SPDX-License-Identifier: Apache-2.0

#include "kernel.hpp"
#include "data_format.h"
#include "quantization_utils.hpp"

namespace {

void quantize_kernel(uint32_t input_tile_id, uint32_t output_tile_id, uint32_t scale, uint32_t zero_point) {
    // ... existing setup code ...
    
    // Read input tile
    // ...
    
    // Process each element
    for (int i = 0; i < TILE_SIZE; ++i) {
        int32_t input_val = read_input(i);
        
        // Calculate quantized value: round(input / scale + zero_point)
        // Assuming fixed-point arithmetic or float conversion depending on implementation
        // Standard formula: out = clamp(round(input / scale + zero_point), 0, 255)
        
        int32_t quantized_val = round_quantize(input_val, scale, zero_point);
        
        // FIX: Clamp to [0, 255] for uint8
        if (quantized_val < 0) {
            quantized_val = 0;
        } else if (quantized_val > 255) {
            quantized_val = 255;
        }
        
        write_output(i, static_cast<uint8_t>(quantized_val));
    }
}

} // namespace

extern "C" {
    void main() {
        // ... entry point ...
    }
}
