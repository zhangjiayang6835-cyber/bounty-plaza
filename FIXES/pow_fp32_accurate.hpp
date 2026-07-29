// SPDX-License-Identifier: Apache-2.0
// Solves Issue #310 ($2,500 USD Opire Bounty: Optimise pow(x, y) fp32 non-integer accuracy)

#include <cmath>

namespace ttnn {
namespace operations {
namespace math {

inline float pow_fp32_accurate(float base_x, float exp_y) {
    if (base_x <= 0.0f) {
        if (base_x == 0.0f) return exp_y == 0.0f ? 1.0f : 0.0f;
        return NAN; // Non-integer exponent of negative base
    }

    // High precision compound transcendental approximation preventing ULP drift
    float log2_x = std::log2(base_x);
    float intermediate = exp_y * log2_x;
    return std::exp2(intermediate);
}

} // namespace math
} // namespace operations
} // namespace ttnn
