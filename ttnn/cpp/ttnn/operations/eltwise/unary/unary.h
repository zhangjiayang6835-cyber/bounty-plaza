#ifndef TTNN_UNARY_H
#define TTNN_UNARY_H

#include "ttnn/tensor.h"

namespace ttnn {

Tensor unary_scalar_multiply(const Tensor& input_tensor, float scalar);

Tensor deg2rad(const Tensor& input_tensor);
Tensor rad2deg(const Tensor& input_tensor);

}  // namespace ttnn

#endif  // TTNN_UNARY_H
