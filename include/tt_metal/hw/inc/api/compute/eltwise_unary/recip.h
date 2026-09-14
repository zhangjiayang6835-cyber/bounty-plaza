#pragma once

#include <cstdint>

namespace ckernel {

/**
 * @brief Initialize reciprocal tile compute operations.
 *
 * @tparam is_fp32_dest_acc_en Whether FP32 accumulation mode is enabled.
 */
template <bool is_fp32_dest_acc_en = false>
inline void recip_tile_init();

/**
 * @brief Compute element-wise reciprocal over a destination tile.
 *
 * @tparam is_fp32_dest_acc_en Whether FP32 accumulation mode is enabled.
 * @param idst Destination tile register identifier.
 */
template <bool is_fp32_dest_acc_en = false>
inline void recip_tile(uint32_t idst);

}
