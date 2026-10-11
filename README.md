# Bounty Plaza Repository

This repository contains bounty issues for the open-source community.

## Bug Fix: FP32 ttnn.cumsum returns NaN after infinity or overflow

### Problem
The compensated FP32 accumulation path in `ttnn.cumsum` has a regression where after the running total becomes +inf or -inf (either from an input containing infinity or from sum overflow), subsequent output elements become NaN due to `inf - inf` producing NaN in the compensation calculation.

### Root Cause
In `ttnn/operations/reduction/cumsum.cpp`, the compensated summation logic uses Kahan-style compensation:
```cpp
float corrected_value = y - running_comp;
float new_comp = (corrected_value - y) + f;
```
When `y` is infinity (±inf), the subtraction `corrected_value - y` becomes `inf - inf = NaN`, which then poisons all subsequent accumulations.

### Fix
Before computing compensation, check if the running total is infinite. If so, skip compensation entirely for that step and let the value pass through directly (matching PyTorch's IEEE behavior). The compensation only matters for finite values where it improves accuracy.

```cpp
// Only use compensation when the running total is finite
float new_comp = (std::isinf(running_total) || std::isnan(running_total)) 
    ? 0.0f 
    : (corrected_value - y) + f;
```

### Changes
- Modified `ttnn/operations/reduction/cumsum.cpp` to guard compensation computation against infinity
- Added regression tests for +inf, -inf, and overflow cases
- Tests cover scan lengths 4, 8, 33 and dimensions 0 and -2

### Verification
- FP32 cumsum now preserves IEEE/PyTorch behavior after ±inf
- NaN inputs still produce NaN outputs (unchanged)
- BF16 and INT32 cumsum unaffected
- FP32 cumprod unaffected
- Existing finite-input behavior unchanged
