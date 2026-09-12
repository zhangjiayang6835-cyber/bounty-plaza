#pragma once

#include <cstdint>

namespace ckernel::sfpu {

/**
 * @brief Initialize SFPU hardware constants for square root operations.
 *
 * @tparam APPROXIMATION_MODE Selects fast approximation or high-precision Taylor series.
 */
template <bool APPROXIMATION_MODE>
void sqrt_init();

/**
 * @brief Compute element-wise square root on destination registers.
 *
 * @tparam APPROXIMATION_MODE Approximation flag.
 * @tparam ITERATIONS Number of Newton-Raphson refinement steps.
 * @tparam fp32_dest_acc_en Whether FP32 destination accumulation is enabled.
 * @tparam FAST_APPROX Fast approximation configuration.
 */
template <bool APPROXIMATION_MODE, int ITERATIONS = 8, bool fp32_dest_acc_en = false, bool FAST_APPROX = false>
inline void calculate_sqrt();

}
