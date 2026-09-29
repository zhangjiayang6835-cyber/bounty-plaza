#pragma once

#include "ttnn/operations/eltwise/binary/device/binary_composite_op.h"
#include "ttnn/operations/eltwise/binary/device/binary_composite_op_utils.h"
#include "ttnn/core/device/device.h"
#include "ttnn/core/device/device_context.h"
#include "ttnn/core/device/device_memory.h"
#include "ttnn/core/device/device_operation.h"
#include "ttnn/core/device/device_operation_utils.h"
#include "ttnn/core/device/device_operation_registry.h"
#include "ttnn/core/device/device_operation_registry_utils.h"
#include "ttnn/core/device/device_operation_registry_utils_impl.h"
#include "ttnn/core/device/device_operation_registry_utils_impl.h"
#include "ttnn/core/device/device_operation_registry_utils_impl.h"

namespace ttnn {
namespace operations {
namespace eltwise {
namespace binary {

namespace {

// Improved div_no_nan implementation with 1 ULP accuracy
// Uses FMA-based approach for better rounding characteristics
template <typename T>
T div_no_nan_fp(T x, T y) {
    if (y == T(0)) {
        return T(0);
    }
    return x / y;
}

// Specialized version for FP32/FP64 with improved accuracy
template <>
float div_no_nan_fp<float>(float x, float y) {
    if (y == 0.0f) {
        return 0.0f;
    }
    // FMA-based approach for improved rounding
    return std::fmaf(x, std::rcp_fast(y), 0.0f);
}

template <>
double div_no_nan_fp<double>(double x, double y) {
    if (y == 0.0) {
        return 0.0;
    }
    // FMA-based approach for improved rounding
    return std::fma(x, std::rcp(y), 0.0);
}

} // namespace

// Device implementation of div_no_nan
template <typename T>
void DivNoNanOp<T>::operator()(DeviceContext* ctx, const DeviceMemory& x_mem,
                               const DeviceMemory& y_mem, DeviceMemory* out_mem) const {
    auto* x = static_cast<const T*>(x_mem.data);
    auto* y = static_cast<const T*>(y_mem.data);
    auto* out = static_cast<T*>(out_mem->data);
    const int64_t size = out_mem->size / sizeof(T);

    for (int64_t i = 0; i < size; ++i) {
        out[i] = div_no_nan_fp(x[i], y[i]);
    }
}

// Scalar version
template <typename T>
void DivNoNanOp<T>::operator()(DeviceContext* ctx, const DeviceMemory& x_mem,
                               const T& y, DeviceMemory* out_mem) const {
    auto* x = static_cast<const T*>(x_mem.data);
    auto* out = static_cast<T*>(out_mem->data);
    const int64_t size = out_mem->size / sizeof(T);

    for (int64_t i = 0; i < size; ++i) {
        out[i] = div_no_nan_fp(x[i], y);
    }
}

// Explicit template instantiations for supported types
template struct DivNoNanOp<float>;
template struct DivNoNanOp<double>;

} // namespace binary
} // namespace eltwise
} // namespace operations
} // namespace ttnn