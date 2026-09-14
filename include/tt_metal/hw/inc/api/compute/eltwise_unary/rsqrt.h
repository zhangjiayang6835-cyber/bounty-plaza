#pragma once

#include <cstdint>

namespace ckernel {

/**
 * @brief Initialize reciprocal square root tile operations.
 */
inline void rsqrt_tile_init();

/**
 * @brief Execute reciprocal square root on a destination tile.
 *
 * @tparam FAST_APPROX Whether fast approximation is requested.
 * @tparam is_fp32_dest_acc_en Whether FP32 accumulation mode is active.
 * @param idst Destination tile index.
 */
template <bool FAST_APPROX = false, bool is_fp32_dest_acc_en = false>
inline void rsqrt_tile(uint32_t idst);

}
