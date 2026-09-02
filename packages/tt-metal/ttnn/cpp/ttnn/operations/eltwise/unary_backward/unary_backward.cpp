#include "ttnn/operations/eltwise/unary_backward/unary_backward.hpp"

#include <optional>
#include <vector>

#include "ttnn/operations/binary/binary.hpp"
#include "ttnn/operations/data_movement/data_movement.hpp"
#include "ttnn/operations/eltwise/unary/unary.hpp"
#include "ttnn/operations/reduction/reduction.hpp"

namespace ttnn {

/**
 * @brief Computes backward gradient for the prod reduction operation.
 *
 * Implements zero-safe gradient computation using non-zero product masking and zero-occurrence counters:
 * - When a reduction group has 0 zeros: grad * prod_nonzero * reciprocal_nonzero
 * - When a reduction group has 1 zero: grad * prod_nonzero * zero_mask
 * - When a reduction group has >= 2 zeros: zero tensor
 *
 * @param grad Upstream incoming gradient tensor.
 * @param input Forward input tensor.
 * @param dim Optional dimension along which reduction was applied (std::nullopt for all dimensions).
 * @param output_mem_config Optional target memory configuration.
 * @return std::vector<Tensor> Vector containing the gradient with respect to input.
 */
std::vector<Tensor> prod_bw(
    const Tensor& grad,
    const Tensor& input,
    const std::optional<int64_t> dim,
    const std::optional<MemoryConfig>& output_mem_config) {
    std::vector<Tensor> grad_tensor;
    auto output_memory_config = output_mem_config.value_or(input.memory_config());

    const bool all_dimensions = !dim.has_value();
    const bool keepdim = !all_dimensions;

    Tensor zero_mask = ttnn::eqz(input, output_memory_config);
    Tensor x_nonzero = ttnn::where(zero_mask, 1.0f, input, output_memory_config);
    Tensor reciprocal_nonzero = ttnn::reciprocal(x_nonzero, output_memory_config);
    Tensor prod_nonzero = ttnn::prod(x_nonzero, dim, keepdim, output_memory_config);

    if (prod_nonzero.layout() == Layout::ROW_MAJOR && prod_nonzero.storage_type() == StorageType::DEVICE) {
        prod_nonzero = ttnn::operations::unary_backward::change_layout_to_tile(prod_nonzero, output_memory_config);
    }

    if (all_dimensions) {
        Tensor temp = ttnn::multiply(prod_nonzero, grad, std::nullopt, output_memory_config);
        Tensor fill_tensor = ttnn::fill_first_val_into_tensor<::bfloat16>(
            temp, temp.dtype(), temp.layout(), temp.device(), output_memory_config);

        Tensor grad_0_zeros = ttnn::multiply(reciprocal_nonzero, fill_tensor, std::nullopt, output_memory_config);
        Tensor grad_1_zero = ttnn::multiply(zero_mask, fill_tensor, std::nullopt, output_memory_config);

        Tensor num_zeros = ttnn::sum(zero_mask, std::nullopt, false, output_memory_config);
        Tensor is_zero_zeros = ttnn::eqz(num_zeros, output_memory_config);
        Tensor is_one_zero = ttnn::eq(num_zeros, 1.0f, std::nullopt, output_memory_config);

        Tensor fill_is_zero = ttnn::fill_first_val_into_tensor<::bfloat16>(
            is_zero_zeros, is_zero_zeros.dtype(), is_zero_zeros.layout(), is_zero_zeros.device(), output_memory_config);
        Tensor fill_is_one = ttnn::fill_first_val_into_tensor<::bfloat16>(
            is_one_zero, is_one_zero.dtype(), is_one_zero.layout(), is_one_zero.device(), output_memory_config);

        Tensor all_dimension_result = ttnn::where(
            fill_is_zero,
            grad_0_zeros,
            ttnn::where(fill_is_one, grad_1_zero, 0.0f, output_memory_config),
            output_memory_config);

        grad_tensor.emplace_back(all_dimension_result);
        return grad_tensor;
    }

    Tensor updated_grad = prod_nonzero;
    auto step = ttsl::SmallVector<uint32_t>({1, 1, 1, 1});
    if (prod_nonzero.logical_shape() != grad.padded_shape()) {
        if (*dim == 3 || *dim == -1) {
            ttsl::SmallVector<int64_t> after_permute_dims = {0, 3, 1, 2};
            Tensor required = ttnn::permute(grad, after_permute_dims, output_memory_config);
            ttsl::SmallVector<uint32_t> start_index = {0, 0, 0, 0};
            ttsl::SmallVector<uint32_t> end_index = {
                grad.padded_shape()[0], 1, grad.padded_shape()[1], grad.padded_shape()[2]};
            Tensor new_slice_tensor = ttnn::slice(required, start_index, end_index, step, std::nullopt);
            after_permute_dims = {0, 2, 3, 1};
            updated_grad = ttnn::permute(new_slice_tensor, after_permute_dims, output_memory_config);
            if (updated_grad.storage_type() != StorageType::DEVICE) {
                Tensor pad_updated_grad = updated_grad.pad_to_tile(1.0f);
                pad_updated_grad = pad_updated_grad.to_layout(Layout::TILE);
                updated_grad = pad_updated_grad.to_device(input.device());
            }
        } else if (*dim == 2 || *dim == -2) {
            ttsl::SmallVector<int64_t> after_permute_dims = {0, 2, 1, 3};
            Tensor required = ttnn::permute(grad, after_permute_dims, output_memory_config);
            ttsl::SmallVector<uint32_t> start_index = {0, 0, 0, 0};
            ttsl::SmallVector<uint32_t> end_index = {
                grad.padded_shape()[0], 1, grad.padded_shape()[1], grad.padded_shape()[3]};
            Tensor new_slice_tensor = ttnn::slice(required, start_index, end_index, step, std::nullopt);
            updated_grad = ttnn::permute(new_slice_tensor, after_permute_dims, output_memory_config);
            if (updated_grad.layout() == Layout::ROW_MAJOR) {
                updated_grad =
                    ttnn::operations::unary_backward::change_layout_to_tile(updated_grad, output_memory_config);
            }
        }
    }

    Tensor temp = ttnn::multiply(
        prod_nonzero,
        (*dim == 1 || *dim == 0 || *dim == -4 || *dim == -3) ? grad : updated_grad,
        std::nullopt,
        output_memory_config);
    if (temp.layout() == Layout::ROW_MAJOR) {
        temp = ttnn::operations::unary_backward::change_layout_to_tile(temp, output_memory_config);
    }

    Tensor num_zeros_dim = ttnn::sum(zero_mask, dim, true, output_memory_config);

    if (*dim == 3 || *dim == -1) {
        Tensor grad_0 = ttnn::bcast(reciprocal_nonzero, temp, ttnn::BcastOpMath::MUL, ttnn::BcastOpDim::W, output_memory_config);
        Tensor grad_1 = ttnn::bcast(zero_mask, temp, ttnn::BcastOpMath::MUL, ttnn::BcastOpDim::W, output_memory_config);
        Tensor cond_0 = ttnn::eqz(num_zeros_dim, output_memory_config);
        Tensor cond_1 = ttnn::eq(num_zeros_dim, 1.0f, std::nullopt, output_memory_config);
        Tensor grad_result = ttnn::where(cond_0, grad_0, ttnn::where(cond_1, grad_1, 0.0f, output_memory_config), output_memory_config);
        grad_tensor.emplace_back(grad_result);
        return grad_tensor;
    }

    if (*dim == 2 || *dim == -2) {
        Tensor grad_0 = ttnn::bcast(reciprocal_nonzero, temp, ttnn::BcastOpMath::MUL, ttnn::BcastOpDim::H, output_memory_config);
        Tensor grad_1 = ttnn::bcast(zero_mask, temp, ttnn::BcastOpMath::MUL, ttnn::BcastOpDim::H, output_memory_config);
        Tensor cond_0 = ttnn::eqz(num_zeros_dim, output_memory_config);
        Tensor cond_1 = ttnn::eq(num_zeros_dim, 1.0f, std::nullopt, output_memory_config);
        Tensor grad_result = ttnn::where(cond_0, grad_0, ttnn::where(cond_1, grad_1, 0.0f, output_memory_config), output_memory_config);
        grad_tensor.emplace_back(grad_result);
        return grad_tensor;
    }

    if (*dim == 1 || *dim == -3) {
        Tensor tensor_1_temp = reciprocal_nonzero;
        Tensor zero_mask_temp = zero_mask;
        if (reciprocal_nonzero.padded_shape()[1] % 32 != 0) {
            ttsl::SmallVector<std::array<uint32_t, 2>> padding = {
                {0, 0}, {0, 32 - (reciprocal_nonzero.padded_shape()[1] % 32)}, {0, 0}, {0, 0}};
            tensor_1_temp = ttnn::pad(reciprocal_nonzero, padding, 0, true, std::nullopt);
            zero_mask_temp = ttnn::pad(zero_mask, padding, 0, true, std::nullopt);
        }
        ttsl::SmallVector<int64_t> after_permute_dims = {0, 2, 3, 1};
        Tensor tensor_1 = ttnn::permute(tensor_1_temp, after_permute_dims, output_memory_config);
        Tensor tensor_mask = ttnn::permute(zero_mask_temp, after_permute_dims, output_memory_config);
        Tensor tensor_2 = ttnn::permute(temp, after_permute_dims, output_memory_config);

        auto padded_shape = ttnn::operations::data_movement::pad_to_tile_shape(tensor_1.padded_shape());
        tensor_2 = tensor_2.to_device(tensor_1.device());
        if (tensor_1.layout() == Layout::ROW_MAJOR) {
            tensor_2 = ttnn::untilize(tensor_2, tensor_1.memory_config());
            if (tensor_2.padded_shape() != padded_shape) {
                tensor_2 = ttnn::pad(
                    tensor_2,
                    padded_shape.to_array_4D(),
                    ttnn::Array4D({0, 0, 0, 0}),
                    0.0f,
                    false,
                    tensor_1.memory_config());
            }
        }

        after_permute_dims = {0, 3, 1, 2};
        Tensor bcast_0 = ttnn::bcast(tensor_1, tensor_2, ttnn::BcastOpMath::MUL, ttnn::BcastOpDim::W, output_memory_config);
        Tensor bcast_1 = ttnn::bcast(tensor_mask, tensor_2, ttnn::BcastOpMath::MUL, ttnn::BcastOpDim::W, output_memory_config);
        Tensor result_0 = permute(bcast_0, after_permute_dims, output_memory_config);
        Tensor result_1 = permute(bcast_1, after_permute_dims, output_memory_config);

        Tensor grad_result_0 = result_0;
        Tensor grad_result_1 = result_1;
        if (reciprocal_nonzero.padded_shape()[1] % 32 != 0) {
            ttsl::SmallVector<uint32_t> start_index = {0, 0, 0, 0};
            ttsl::SmallVector<uint32_t> end_index = {
                input.padded_shape()[0], input.padded_shape()[1], input.padded_shape()[2], input.padded_shape()[3]};
            auto step_slice = ttsl::SmallVector<uint32_t>({1, 1, 1, 1});
            grad_result_0 = ttnn::slice(result_0, start_index, end_index, step_slice, std::nullopt);
            grad_result_1 = ttnn::slice(result_1, start_index, end_index, step_slice, std::nullopt);
        }

        Tensor cond_0 = ttnn::eqz(num_zeros_dim, output_memory_config);
        Tensor cond_1 = ttnn::eq(num_zeros_dim, 1.0f, std::nullopt, output_memory_config);
        Tensor final_grad = ttnn::where(cond_0, grad_result_0, ttnn::where(cond_1, grad_result_1, 0.0f, output_memory_config), output_memory_config);
        grad_tensor.emplace_back(final_grad);
        return grad_tensor;
    }

    Tensor tensor_1_temp = reciprocal_nonzero;
    Tensor zero_mask_temp = zero_mask;
    if (reciprocal_nonzero.padded_shape()[0] % 32 != 0) {
        ttsl::SmallVector<std::array<uint32_t, 2>> padding = {
            {0, 32 - (reciprocal_nonzero.padded_shape()[0] % 32)}, {0, 0}, {0, 0}, {0, 0}};
        tensor_1_temp = ttnn::pad(reciprocal_nonzero, padding, 0, true, std::nullopt);
        zero_mask_temp = ttnn::pad(zero_mask, padding, 0, true, std::nullopt);
    }
    ttsl::SmallVector<int64_t> after_permute_dims = {3, 1, 2, 0};
    Tensor tensor_1 = ttnn::permute(tensor_1_temp, after_permute_dims, output_memory_config);
    Tensor tensor_mask = ttnn::permute(zero_mask_temp, after_permute_dims, output_memory_config);
    Tensor tensor_2 = ttnn::permute(temp, after_permute_dims, output_memory_config);

    auto padded_shape = ttnn::operations::data_movement::pad_to_tile_shape(tensor_1.padded_shape());
    tensor_2 = tensor_2.to_device(tensor_1.device());
    if (tensor_1.layout() == Layout::ROW_MAJOR) {
        tensor_2 = ttnn::untilize(tensor_2, tensor_1.memory_config());
        if (tensor_2.padded_shape() != padded_shape) {
            tensor_2 = ttnn::pad(
                tensor_2,
                padded_shape.to_array_4D(),
                ttnn::Array4D({0, 0, 0, 0}),
                0.0f,
                false,
                tensor_1.memory_config());
        }
    }

    after_permute_dims = {3, 1, 2, 0};
    Tensor bcast_0 = ttnn::bcast(tensor_1, tensor_2, ttnn::BcastOpMath::MUL, ttnn::BcastOpDim::W, output_memory_config);
    Tensor bcast_1 = ttnn::bcast(tensor_mask, tensor_2, ttnn::BcastOpMath::MUL, ttnn::BcastOpDim::W, output_memory_config);
    Tensor result_0 = permute(bcast_0, after_permute_dims, output_memory_config);
    Tensor result_1 = permute(bcast_1, after_permute_dims, output_memory_config);

    Tensor grad_result_0 = result_0;
    Tensor grad_result_1 = result_1;
    if (reciprocal_nonzero.padded_shape()[0] % 32 != 0) {
        ttsl::SmallVector<uint32_t> start_index = {0, 0, 0, 0};
        ttsl::SmallVector<uint32_t> end_index = {
            input.padded_shape()[0], input.padded_shape()[1], input.padded_shape()[2], input.padded_shape()[3]};
        auto step_slice = ttsl::SmallVector<uint32_t>({1, 1, 1, 1});
        grad_result_0 = ttnn::slice(result_0, start_index, end_index, step_slice, std::nullopt);
        grad_result_1 = ttnn::slice(result_1, start_index, end_index, step_slice, std::nullopt);
    }

    Tensor cond_0 = ttnn::eqz(num_zeros_dim, output_memory_config);
    Tensor cond_1 = ttnn::eq(num_zeros_dim, 1.0f, std::nullopt, output_memory_config);
    Tensor final_grad = ttnn::where(cond_0, grad_result_0, ttnn::where(cond_1, grad_result_1, 0.0f, output_memory_config), output_memory_config);
    grad_tensor.emplace_back(final_grad);
    return grad_tensor;
}

}  // namespace ttnn
