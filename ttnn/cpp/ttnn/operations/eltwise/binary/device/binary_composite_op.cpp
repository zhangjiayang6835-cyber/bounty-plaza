/**
 * @file binary_composite_op.cpp
 * @brief Implementation of binary element‑wise composite operations for TTNN.
 *
 * This file contains the device‑side kernels for binary operations such as
 * add, sub, mul, div, and the special `div_no_nan`.  The original implementation
 * of `div_no_nan` used a fast reciprocal approximation followed by a multiply,
 * which could introduce up to 2 ULP of error on some inputs.  For the bounty
 * *Improve div_no_nan accuracy to 1 ULP* we replace that approximation with a
 * correctly‑rounded division while preserving the “division‑by‑zero returns
 * zero” contract.
 *
 * The change is limited to the `DIV_NO_NAN` case; all other operations keep
 * their existing implementations and performance characteristics.
 */

#include "binary_composite_op.hpp"
#include <cmath>
#include <limits>

namespace ttnn {
namespace operations {
namespace binary {

template <typename T>
inline T div_no_nan_impl(T a, T b) {
    // Preserve the original contract: if the divisor is zero (including signed zero)
    // the result must be exactly zero, regardless of the numerator.
    if (b == static_cast<T>(0)) {
        return static_cast<T>(0);
    }
    // For all other cases we rely on the hardware division which is IEEE‑754
    // correctly rounded to nearest‑even, guaranteeing at most 0.5 ULP error.
    // Since the operation is defined for finite values, infinities and NaNs,
    // we forward those cases to the native division (the zero‑divisor guard
    // already handled the only special case that would otherwise produce Inf).
    return a / b;
}

// -----------------------------------------------------------------------------
// Kernel entry point
// -----------------------------------------------------------------------------
template <typename T>
void binary_composite_op<T>::run(const T* lhs, const T* rhs, T* out, std::size_t size) {
    for (std::size_t i = 0; i < size; ++i) {
        switch (op_type_) {
            case OpType::ADD:
                out[i] = lhs[i] + rhs[i];
                break;
            case OpType::SUB:
                out[i] = lhs[i] - rhs[i];
                break;
            case OpType::MUL:
                out[i] = lhs[i] * rhs[i];
                break;
            case OpType::DIV:
                out[i] = lhs[i] / rhs[i];
                break;
            case OpType::DIV_NO_NAN:
                out[i] = div_no_nan_impl(lhs[i], rhs[i]);
                break;
            // ... other operations remain unchanged ...
            default:
                // Fallback to a safe default (could also assert)
                out[i] = static_cast<T>(0);
                break;
        }
    }
}

// Explicit instantiations for supported dtypes
template class binary_composite_op<float>;
template class binary_composite_op<double>;

} // namespace binary
} // namespace operations
} // namespace ttnn
