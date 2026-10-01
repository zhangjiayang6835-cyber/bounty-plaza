To address the issue where the output rows don't sum to 1 for non-32-widths, we need to ensure the padded elements are set to -inf in the fused small-kernel paths.

Here's the code modification:

```cpp
// Inside the fused scale-mask-softmax function

// After applying the user mask
if (logical_width % 32 != 0) {
    int64_t padding_index = (batch_size * sequence_length + position) % logical_width;
    if (padding_index >= sequence_length) {
        data[padding_index] = -inf;
    }
}

// Continue with the rest of the computation
```

This addition ensures that padded elements are correctly set to -inf, making the output rows sum to approximately 1, as expected.