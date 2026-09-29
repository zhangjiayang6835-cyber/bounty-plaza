// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2024 Tenstorrent Inc. All rights reserved.

#include "softmax.hpp"

#include <cmath>

#include "ttnn/operations/normalization/softmax/device/kernels/attention/compute/softmax_common.hpp"

namespace ttnn::operations::normalization::softmax::device::kernels::attention::compute {

// Helper to apply padded mask for non-32-multiple widths
static inline void apply_padded_mask(
    float* output,
    const uint32_t* mask,
    const uint32_t num_rows,
    const uint32_t num_cols,
    const uint32_t tile_width = 32) {
    const uint32_t logical_width = num_cols;
    const uint32_t padded_width = ((logical_width + tile_width - 1) / tile_width) * tile_width;

    if (padded_width == logical_width) {
        return; // No padding needed
    }

    for (uint32_t row = 0; row < num_rows; ++row) {
        for (uint32_t col = logical_width; col < padded_width; ++col) {
            const uint32_t idx = row * padded_width + col;
            if (mask && (mask[idx / 32] & (1 << (idx % 32)))) {
                output[idx] = -INFINITY;
            } else {
                output[idx] = -INFINITY; // Always mask padded columns
            }
        }
    }
}

void scale_mask_softmax(
    float* output,
    const float* input,
    const float* mask,
    const float scale,
    const uint32_t num_rows,
    const uint32_t num_cols,
    const bool is_causal) {

    // Apply user mask first
    for (uint32_t i = 0; i < num_rows * num_cols; ++i) {
        if (mask && (mask[i / 32] & (1 << (i % 32)))) {
            output[i] = -INFINITY;
        } else {
            output[i] = input[i] * scale;
        }
    }

    // Apply padded mask for non-32-multiple widths
    apply_padded_mask(output, nullptr, num_rows, num_cols);

    // Softmax computation
    for (uint32_t row = 0; row < num_rows; ++row) {
        float max_val = -INFINITY;
        float sum = 0.0f;

        // Find max
        for (uint32_t col = 0; col < num_cols; ++col) {
            const float val = output[row * num_cols + col];
            if (val > max_val) {
                max_val = val;
            }
        }

        // Subtract max and compute exp
        for (uint32_t col = 0; col < num_cols; ++col) {
            const uint32_t idx = row * num_cols + col;
            output[idx] = std::exp(output[idx] - max_val);
            sum += output[idx];
        }

        // Normalize
        const float inv_sum = 1.0f / sum;
        for (uint32_t col = 0; col < num_cols; ++col) {
            output[row * num_cols + col] *= inv_sum;
        }
    }
}

void scale_mask_softmax_in_place(
    float* input_output,
    const float* mask,
    const float scale,
    const uint32_t num_rows,
    const uint32_t num_cols,
    const bool is_causal) {

    // Apply user mask and scale
    for (uint32_t i = 0; i < num_rows * num_cols; ++i) {
        if (mask && (mask[i / 32] & (1 << (i % 32)))) {
            input_output[i] = -INFINITY;
        } else {
            input_output[i] *= scale;
        }
    }

    // Apply padded mask for non-32-multiple widths
    apply_padded_mask(input_output, nullptr, num_rows, num_cols);

    // In-place softmax
    for (uint32_t row = 0; row < num_rows; ++row) {
        float max_val = -INFINITY;
        float sum = 0.0f;

        for (uint32_t col = 0; col < num_cols; ++col) {
            const float val = input_output[row * num_cols + col];
            if (val > max_val) {
                max_val = val;
            }
        }

        for (uint32_t col = 0; col < num_cols; ++col) {
            const uint32_t idx = row * num_cols + col;
            input_output[idx] = std::exp(input_output[idx] - max_val);
            sum += input_output[idx];
        }

        const float inv_sum = 1.0f / sum;
        for (uint32_t col = 0; col < num_cols; ++col) {
            input_output[row * num_cols + col] *= inv_sum;
        }
    }
}

void attention_softmax_(
    float* output,
    const float* input,
    const float* mask,
    const float scale,
    const uint32_t num_rows,
    const uint32_t num_cols,
    const bool is_causal) {

    // Combined implementation for attention softmax
    for (uint32_t i = 0; i < num_rows * num_cols; ++i) {
        if (mask && (mask[i / 32] & (1 << (i % 32)))) {
            output[i] = -INFINITY;
        } else {
            output[i] = input[i] * scale;
        }
    }

    // Apply padded mask for non-32-multiple widths
    apply_padded_mask(output, nullptr, num_rows, num_cols);

    // Handle causal mask if needed
    if (is_causal) {
        for (uint32_t row = 0; row < num_rows; ++row) {
            for (uint32_t col = row + 1; col < num_cols; ++col) {
                output[row * num_cols + col] = -INFINITY;
            }
        }
    }

    // Softmax computation
    for (uint32_t row = 0; row < num_rows; ++row) {
        float max_val = -INFINITY;
        float sum = 0.0f;

        for (uint32_t col = 0; col < num_cols; ++col) {
            const float val = output[row * num_cols + col];
            if (val > max_val) {
                max_val = val;
            }
        }

        for (uint32_t col = 0; col < num_cols; ++col) {
            const uint32_t idx = row * num_cols + col;
            output[idx] = std::exp(output[idx] - max_val);
            sum += output[idx];
        }

        const float inv_sum = 1.0f / sum;
        for (uint32_t col = 0; col < num_cols; ++col) {
            output[row * num_cols + col] *= inv_sum;
        }
    }
}

} // namespace ttnn::operations::normalization::softmax::device::kernels::attention::compute
```
    },
    {
      "path": "tests/test_softmax_padding_fix.py",
      "content": "# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2024 Tenstorrent Inc. All rights reserved.

import pytest
import torch
import ttnn
import numpy as np

# Test cases for non-32-multiple widths
TEST_WIDTHS = [17, 50, 197, 1001, 32, 64]  # Include aligned widths for verification
TEST_DTYPES = [torch.float32, torch.bfloat16]
TEST_MASK_TYPES = ["broadcast", "causal"]


def pytorch_softmax_reference(input, mask, scale, is_causal=False):
    """PyTorch reference implementation for comparison"""
    input = input.clone()
    if mask is not None:
        input = input.masked_fill(mask == 0, float('-inf'))
    if is_causal:
        causal_mask = torch.triu(torch.ones_like(input), diagonal=1).bool()
        input = input.masked_fill(causal_mask, float('-inf'))
    input = input * scale
    return torch.softmax(input, dim=-1)


@pytest.mark.parametrize("width", TEST_WIDTHS)
@pytest.mark.parametrize("dtype", TEST_DTYPES)
@pytest.mark.parametrize("mask_type", TEST_MASK_TYPES)
def test_scale_mask_softmax_padding(width, dtype, mask_type):
    """Test scale_mask_softmax with non-32-multiple widths"""
    num_rows = 16
    is_causal = (mask_type == "causal")

    # Create test input
    torch_input = torch.randn(num_rows, width, dtype=dtype)
    if dtype == torch.bfloat16:
        torch_input = torch_input.to(torch.float32)  # ttnn may require conversion

    # Create mask
    if mask_type == "broadcast":
        torch_mask = torch.randint(0, 2, (num_rows, width), dtype=torch.uint8)
    else:  # causal
        torch_mask = None

    # PyTorch reference
    pytorch_output = pytorch_softmax_reference(
        torch_input, torch_mask, 1.0, is_causal
    )

    # ttnn implementation
    ttnn_input = ttnn.from_torch(torch_input)
    if torch_mask is not None:
        ttnn_mask = ttnn.from_torch(torch_mask)
    else:
        ttnn_mask = None

    ttnn_output = ttnn.scale_mask_softmax(
        ttnn_input,
        mask=ttnn_mask,
        scale=1.0,
        is_causal=is_causal
    )

    # Convert back to torch for comparison
    ttnn_output_torch = ttnn_output.to_torch()

    # Verify row sums are approximately 1
    row_sums = ttnn_output_torch.sum(dim=-1)
    assert torch.allclose(row_sums, torch.ones_like(row_sums), atol=1e-5), \
        f"Row sums not ≈1 for width={width}, dtype={dtype}, mask={mask_type}"

    # Compare with PyTorch reference
    assert torch.allclose(
        ttnn_output_torch.to(torch.float32),
        pytorch_output.to(torch.float32),
        atol=1e-5
    ), f"Output mismatch for width={width}, dtype={dtype}, mask={mask_type}"


@pytest.mark.parametrize("width", TEST_WIDTHS)
@pytest.mark.parametrize("dtype", TEST_DTYPES)
@pytest.mark.parametrize("mask_type", TEST_MASK_TYPES)
def test_scale_mask_softmax_in_place_padding(width, dtype, mask_type):
    """Test in-place version with non-32-multiple widths"""
    num_rows = 16
    is_causal = (mask_type == "causal")

    torch_input = torch.randn(num_rows, width, dtype=dtype)
    if dtype == torch.bfloat16:
        torch_input = torch_input.to(torch.float32)

    if mask_type == "broadcast":
        torch_mask = torch.randint(0, 2, (num_rows, width), dtype=torch.uint8)
    else:
        torch_mask = None

    pytorch_output = pytorch_softmax_reference(
        torch_input.clone(), torch_mask, 1.0, is_causal
    )

    # ttnn in-place version
    ttnn_input = ttnn.from_torch(torch_input)
    if torch_mask is not None:
        ttnn_mask = ttnn.from_torch(torch_mask)
    else:
        ttnn_mask = None

    ttnn.scale_mask_softmax_in_place(
        ttnn_input,
        mask=ttnn_mask,
        scale=1.0,
        is_causal=is_causal
    )

    ttnn_output_torch = ttnn_input.to_torch()

    # Verify row sums
    row_sums = ttnn_output_torch.sum(dim=-1)
    assert torch.allclose(row_sums, torch.ones_like(row_sums), atol=1e-5), \
        f"Row sums not ≈1 for in-place, width={width}, dtype={dtype}, mask={mask_type}"

    # Compare with reference
    assert torch.allclose(
        ttnn_output_torch.to(torch.float32),
        pytorch_output.to(torch.float32),
        atol=1e-5
    ), f"In-place output mismatch for width={width}, dtype={dtype}, mask={mask_type}"


@pytest.mark.parametrize("width", TEST_WIDTHS)
@pytest.mark.parametrize("dtype", TEST_DTYPES)
def test_attention_softmax_padding(width, dtype):
    """Test attention_softmax_ with non-32-multiple widths"""
    num_rows = 16

    torch_input = torch.randn(num_rows, width, dtype=dtype)
    if dtype == torch.bfloat16:
        torch_input = torch_input.to(torch.float32)

    # Test both causal and broadcast cases
    for is_causal in [True, False]:
        if is_causal:
            torch_mask = None
        else:
            torch_mask = torch.randint(0, 2, (num_rows, width), dtype=torch.uint8)

        pytorch_output = pytorch_softmax_reference(
            torch_input.clone(), torch_mask, 1.0, is_causal
        )

        ttnn_input = ttnn.from_torch(torch_input)
        if torch_mask is not None:
            ttnn_mask = ttnn.from_torch(torch_mask)
        else:
            ttnn_mask = None

        ttnn_output = ttnn.transformer.attention_softmax_(
            ttnn_input,
            mask=ttnn_mask,
            scale=1.0,
            is_causal=is_causal
        )

        ttnn_output_torch = ttnn_output.to_torch()

        # Verify row sums
        row_sums = ttnn_output_torch.sum(dim=-1)
        assert torch.allclose(row_sums, torch.ones_like(row_sums), atol=1e-5), \
            f"Row sums not ≈1 for attention_softmax, width={width}, dtype={dtype}, causal={is_causal}"

        # Compare with reference
        assert torch.allclose(
            ttnn_output_torch.to(torch.float32),
            pytorch_output.to(torch.float32),
            atol=1e-5
        ), f"attention_softmax output mismatch for width={width}, dtype={dtype}, causal={is_causal}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
