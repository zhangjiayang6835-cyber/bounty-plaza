#include "ttnn/kernels/division.hpp"
#include "ttnn/operations/primary.hpp"
#include "ttnn/types.hpp"
#include <cmath>
#include <limits>

namespace ttnn {

namespace {

void calculate_div_int32_body(
    const int32_t a,
    const int32_t b,
    int32_t& quotient,
    int32_t& remainder,
    const RoundingMode rounding_mode
) {
    // Handle undefined cases first
    if (a == std::numeric_limits<int32_t>::min()) {
        if (b == 0) {
            // Undefined behavior: division by zero
            quotient = std::numeric_limits<int32_t>::min();
            remainder = std::numeric_limits<int32_t>::min();
            return;
        }
        if (b == -1) {
            // Undefined behavior: INT32_MIN / -1 overflow
            quotient = std::numeric_limits<int32_t>::min();
            remainder = 0;
            return;
        }
    }

    // Compute absolute values using a wider type to avoid overflow
    int64_t a_abs = static_cast<int64_t>(a) == std::numeric_limits<int32_t>::min()
                   ? static_cast<int64_t>(std::numeric_limits<int32_t>::max()) + 1   // 2^31
                   : std::abs(a);
    int64_t b_abs = std::abs(static_cast<int64_t>(b));

    // Compute quotient using 64-bit arithmetic
    int64_t q = a_abs / b_abs;

    // Compute remainder
    int64_t r = a_abs - q * b_abs;

    // Handle residual magnitude conversion
    sfpi::vFloat r_float;
    if (r >= 0) {
        r_float = sfpi::convert<sfpi::vFloat>(r);
    } else {
        // For the overflowed case, set the float to 2^31 explicitly
        r_float = sfpi::convert<sfpi::vFloat>(static_cast<int64_t>(std::numeric_limits<int32_t>::max()) + 1);
    }

    // Preserve sign flag
    bool r_negative = (r < 0);

    // Apply residual correction
    if (rounding_mode == RoundingMode::FLOOR) {
        if (r_negative) {
            r_float += sfpi::convert<sfpi::vFloat>(b_abs);
            q -= 1;
        }
    } else if (rounding_mode == RoundingMode::TRUNC) {
        if (r_negative) {
            r_float += sfpi::convert<sfpi::vFloat>(b_abs);
            q -= 1;
        }
    }

    // Convert back to int32
    quotient = static_cast<int32_t>(q);
    remainder = static_cast<int32_t>(r_float);

    // Apply sign to quotient and remainder
    if ((a < 0) != (b < 0)) {
        quotient = -quotient;
        remainder = -remainder;
    }
}

} // namespace

} // namespace ttnn
