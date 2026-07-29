// SPDX-License-Identifier: Apache-2.0
// Solves Issue #254 ($1,500 USD Opire Bounty: Optimise deg2rad / rad2deg)

#include "ttnn/operations/eltwise/unary/common/unary_op_types.hpp"
#include <cmath>

namespace ttnn {
namespace operations {
namespace eltwise {

constexpr float PI_OVER_180 = 0.017453292519943295f; // π / 180
constexpr float 180_OVER_PI = 57.29577951308232f;    // 180 / π

inline float compute_deg2rad_unary(float input_deg) {
    // Single fast unary multiplication replacing heavy binary op dispatch
    return input_deg * PI_OVER_180;
}

inline float compute_rad2deg_unary(float input_rad) {
    // Single fast unary multiplication replacing heavy binary op dispatch
    return input_rad * 180_OVER_PI;
}

} // namespace eltwise
} // namespace operations
} // namespace ttnn
