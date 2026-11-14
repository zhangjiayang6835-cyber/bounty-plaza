#include <stdint.h>
#include "dataflow_api.h"

void kernel_main() {
    uint32_t src_addr  = get_arg_val<uint32_t>(0);
    uint32_t mask_addr = get_arg_val<uint32_t>(1);
    uint32_t num_tiles = get_arg_val<uint32_t>(2);
    uint32_t mask_h    = get_arg_val<uint32_t>(3); // Actual mask height in tiles
    uint32_t mask_w    = get_arg_val<uint32_t>(4);
    uint32_t is_causal = get_arg_val<uint32_t>(5);
    uint32_t batch_size = get_arg_val<uint32_t>(6);

    constexpr uint32_t cb_id_in0 = 0;
    constexpr uint32_t cb_id_mask = 2;

    uint32_t tile_size = get_tile_size(cb_id_in0);
    uint32_t mask_tile_size = get_tile_size(cb_id_mask);

    uint32_t i = 0;
    for (uint32_t b = 0; b < batch_size; b++) {
        for (uint32_t t = 0; t < num_tiles; t++) {
            // Issue 2 & 3: Correct wrapping and batch boundary handling
            // We use the global tile index to determine the mask row
            uint32_t global_row_idx = (b * num_tiles + t) / mask_w;
            uint32_t mask_tile_idx;

            if (is_causal) {
                // Causal interleaved mask readers wrap rows using the mask’s height
                uint32_t row_within_mask = global_row_idx % mask_h;
                uint32_t col_within_mask = t % mask_w;
                mask_tile_idx = row_within_mask * mask_w + col_within_mask;
            } else {
                mask_tile_idx = t % (mask_h * mask_w);
            }

            cb_reserve_back(cb_id_mask, 1);
            uint32_t l1_write_addr = get_write_ptr(cb_id_mask);
            
            // Read mask tile from interleaved memory
            uint64_t mask_noc_addr = get_noc_addr(mask_tile_idx, mask_addr);
            noc_async_read(mask_noc_addr, l1_write_addr, mask_tile_size);
            noc_async_read_barrier();
            
            cb_push_back(cb_id_mask, 1);
        }
    }
}
