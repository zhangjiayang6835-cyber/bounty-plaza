#pragma once

#include <optional>
#include <vector>

#include "ttnn/tensor/tensor.hpp"
#include "ttnn/types.hpp"

namespace ttnn {

/**
 * @brief Computes backward gradient for the prod reduction operation.
 *
 * Mathematically handles exact zeros in the input tensor to guarantee finite gradients:
 * - 0 zeros: grad * prod(input) / input
 * - 1 zero: grad * prod_{j != m}(input_j) at zero index m, 0 elsewhere
 * - 2+ zeros: 0 everywhere
 *
 * @param grad Upstream incoming gradient tensor.
 * @param input Forward input tensor.
 * @param dim Optional dimension along which reduction was applied (std::nullopt for all dimensions).
 * @param output_mem_config Optional target memory configuration.
 * @return std::vector<Tensor> Vector containing gradient tensor with respect to input.
 */
std::vector<Tensor> prod_bw(
    const Tensor& grad,
    const Tensor& input,
    const std::optional<int64_t> dim = std::nullopt,
    const std::optional<MemoryConfig>& output_mem_config = std::nullopt);

}  // namespace ttnn
