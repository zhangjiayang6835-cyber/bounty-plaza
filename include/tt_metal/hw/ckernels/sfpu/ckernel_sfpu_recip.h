#pragma once

#include <cstdint>

namespace ckernel::sfpu {

/**
 * @brief Initialize SFPU hardware constants for reciprocal operations.
 *
 * @tparam APPROXIMATION_MODE Selects fast 7b approximation or 24b precise mode.
 * @tparam is_fp32_dest_acc_en Whether destination accumulation is FP32.
 * @tparam ITERATIONS Number of refinement cycles.
 */
template <bool APPROXIMATION_MODE, bool is_fp32_dest_acc_en = false, int ITERATIONS = 8>
void recip_init();

/**
 * @brief Compute element-wise reciprocal 1/x.
 *
 * @tparam APPROXIMATION_MODE Approximation flag.
 * @tparam is_fp32_dest_acc_en Whether FP32 destination accumulation is enabled.
 * @tparam ITERATIONS Number of refinement cycles.
 */
template <bool APPROXIMATION_MODE, bool is_fp32_dest_acc_en = false, int ITERATIONS = 8>
inline void calculate_recip();

}
