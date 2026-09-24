To fix the distributed LayerNorm and RMSNorm 2D-core-grid row-stride corruption, we need to correctly compute the row stride and row start for each core. Here's the adjusted code:

```python
def _compute_layer_norm_2d(
    self, 
    inputs: Tensor,
    weight: Tensor,
    bias: Tensor,
    eps: float,
    use_2d_core_grid: bool,
) -> Tensor:
    if self.use_2d_core_grid:
        (batch_size, sequence_len, input_size) = inputs.shape
        (num_weights, _) = weight.shape
        assert sequence_len == self.sequence_len
        assert num_weights == input_size
        # pre-all-gather case
        # The row stride is the number of rows each core has
        rows_per_core = (sequence_len + self.world_size - 1) // self.world_size
        # Set row_stride and row_start for the pre-all-gather path
        row_stride = rows_per_core
        row_start = self.core_idx * rows_per_core
        # Compute the output
        output = self._layer_norm_2d_pre_all_gather(
            inputs, weight, bias, eps, row_start, row_stride
        )
        return output
    else:
        # Original 1D case
        return self._compute_layer_norm_1d(inputs, weight, bias, eps)
```

For the post-all-gather case:

```python
def _rms_norm_post_all_gather(
    self, 
    inputs: Tensor,
    weight: Tensor,
    bias: Tensor,
    eps: float,
) -> Tensor:
    if self.use_2d_core_grid:
        (batch_size, sequence_len, input_size) = inputs.shape
        (num_weights, _) = weight.shape
        assert sequence_len == self.sequence_len
        assert num_weights == input_size
        # post-all-gather case
        rows_per_core = (sequence_len + self.world_size - 1) // self.world_size
        # Set row_stride and row_start for the post-all-gather path
        row_stride = rows_per_core
        row_start = self.core_idx * rows_per_core
        # Compute the output
        output = self._rms_norm_post_all_gather_impl(
            inputs, weight, bias, eps, row_start, row_stride
        )
        return output
    else:
        # Original 1D case
        return self._rms_norm_post_all_gather_1d(inputs, weight, bias, eps)
```

These adjustments ensure that each core correctly computes its assigned rows and strides, resolving the row-stride issue.