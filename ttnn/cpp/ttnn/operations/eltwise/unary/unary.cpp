#include <cmath>
#include "ttnn/operations/eltwise/unary/unary.h"

namespace ttnn {

Tensor deg2rad(const Tensor& input_tensor) {
    constexpr float DEG_TO_RAD = 0.017453292519943295f;
    return unary_scalar_multiply(input_tensor, DEG_TO_RAD);
}

Tensor rad2deg(const Tensor& input_tensor) {
    constexpr float RAD_TO_DEG = 57.29577951308232f;
    return unary_scalar_multiply(input_tensor, RAD_TO_DEG);
}

Tensor unary_scalar_multiply(const Tensor& input_tensor, float scalar) {
    Tensor output_tensor(input_tensor.shape());
    for (size_t i = 0; i < input_tensor.size(); ++i) {
        output_tensor[i] = input_tensor[i] * scalar;
    }
    return output_tensor;
}

}  // namespace ttnn
