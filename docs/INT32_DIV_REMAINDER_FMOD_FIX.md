# INT32_MIN Correctness Fix for int32 div, remainder, fmod, and scalar promotion

Technical documentation for the `$5,000` bounty
[tenstorrent/tt-metal#55502](https://github.com/tenstorrent/tt-metal/issues/55502)
("Fix INT_MIN correctness in int32 div, remainder, fmod, and scalar promotion"),
which also closes
[tenstorrent/tt-metal#51476](https://github.com/tenstorrent/tt-metal/issues/51476)
("ttnn.div int32 (trunc/floor): dividend -2\*\*31 returns -1").

This document records the root cause, the fix that landed in upstream
[tenstorrent/tt-metal#55506](https://github.com/tenstorrent/tt-metal/pull/55506)
(merged into `main` as `7a0718b`), and how every acceptance criterion of the
bounty is satisfied.

---

## 1. Summary

`ttnn.div` with int32 operands and `rounding_mode="trunc"` / `"floor"` produced
silent, finite, plausible-looking wrong results for the dividend `INT32_MIN`
(`-2147483648`, bit pattern `0x80000000`) on both Wormhole (WH) and Blackhole
(BH). The same family of defects affected tensor `remainder`, `fmod`, and the
scalar-dispatch / type-promotion paths.

The fix:

- repairs the missing `INT32_MIN` guard at the residual-correction conversion
  site of the int32 division kernels on both architectures, including the
  residual **sign** (a value-only clamp is not sufficient),
- fixes the corresponding `INT32_MIN` edge cases in the remainder and fmod
  kernels with agreed reference semantics,
- keeps integer-tensor + integer-scalar operations exact, and promotes
  integer-tensor + floating-point-scalar operations to FP32,
- aligns Wormhole and Blackhole on the supported input set,
- adds regression coverage for tensor-tensor and tensor-scalar paths, both
  rounding modes, both architectures, both divisor signs, and divisors around
  the known failure thresholds, and
- neither changes results outside the affected edge cases nor introduces
  register spills or a performance regression (it is, in fact, faster).

---

## 2. Background

### 2.1 The failure mode

The int32 division kernels estimate the quotient and then run a
residual-correction step. During that step the intermediate integer *magnitudes*
are converted to FP32. `INT32_MIN` has the bit pattern `0x80000000`; through the
SFPI sign-magnitude-to-float conversion (`sfpi::convert<vFloat>(vMag)`) that bit
pattern is reinterpreted as sign=1, magnitude=0, i.e. **`-0.0f`** instead of the
valid magnitude `2**31`. The correction term then collapses to zero and the
entire quotient is lost, leaving only the `±1` that the recovery step adds.

Concrete behaviour before the fix (`a = -2147483648`):

| b                | rounding | kernel | torch | abs err |
|------------------|----------|--------|-------|---------|
| `2097152` (= 2^21, WH) | trunc | **-1** | -1024 | 1023 |
| `2097152`           | floor | **-2** | -1024 | 1022 |
| `239823930`         | trunc | **-1** | -8    | 7 |
| `1073741824` (= 2^30) | trunc | **-1** | -2  | 1 |

Across the affected band the returned magnitude is pinned at `1` while the true
magnitude is anything from `2` to `1024` — up to 99.90% relative error on
ordinary in-range integers, against an op whose unit test asserts bit-exact
equality with the torch golden.

### 2.2 Why `INT32_MIN` is not an exotic input

`-2**31` is the identity element for an int32 max-reduction, the conventional
"unset" sentinel in index/mask tensors, and where int32 arithmetic lands when it
wraps. It is already known to break sibling ops: see open issues #44750 and
#49803 (int32 reduce min/max on `INT32_MIN`).

### 2.3 Affected set size

With `a = INT32_MIN` on WH, every divisor in the band `2**21 <= |b| <= 2**30`
returns a wrong quotient — 49.90% of the 4,294,967,295 non-zero int32 divisors,
counted exactly. BH has the same shape with the band starting at `2**22`.

---

## 3. Root cause

Both affected kernels
(`tt_metal/hw/ckernels/wormhole_b0/.../ckernel_sfpu_div_int32_floor.h` and
`tt_metal/hw/ckernels/blackhole/.../ckernel_sfpu_div_int32_floor.h`) already
guard the `INT32_MIN` conversion at **two** of the **three** identical
conversion sites (`b_f` and `a_f` are clamped to `0x1.0p31f` when they convert
negative). The **third** conversion — the residual `r_f =
convert<vFloat>(abs(r))` — is unguarded. `r` becomes `-0.0f`, the correction is
computed as `-0.0f * inv_b_f`, rounds to integer `0`, and the quotient is lost.

Two distinct defects combine:

1. **Residual magnitude**: `abs(INT32_MIN)` returns the unchanged bit pattern
   `0x80000000` (documented in `sfpi_lib.h`: *"Even though mostneg returns
   unchanged bit pattern, this returns vMag"*). Converting it through the
   sign-magnitude path yields `-0.0f`, not `2**31`.
2. **Residual sign**: the downstream `v_if(r >= 0)` (WH) / `v_if(r < 0)` (BH)
   reads the same `0x80000000` as a *negative* remainder, so even a value-only
   clamp applies the (now correct) correction in the **wrong direction**. A
   value-only clamp is provably insufficient: emulated, the worst absolute error
   goes from 1024 to **2048** on WH (512 to 1024 on BH).

The `2**34` (WH) / `2**33` (BH) mantissa-alignment constants set the collapse
threshold: the initial quotient is rounded in steps of `2**11` on WH and `2**10`
on BH, so the estimate collapses to zero for `|b| >= 2**21` (WH) / `2**22` (BH).

The two implementations are *not* identical — WH uses a software reciprocal with
11-bit chunked `SFPMAD` products and `2**34` mantissa alignment; BH uses
`SFPARECIP` + `SFPMUL24` and `2**33` alignment — but the guard pattern, and the
omission, are identical in both.

### 3.1 Why the existing test suite could not see this

`INT32_MIN` was in the test data, but both operands were monotone-descending
`linspace` tensors over the same index, so `a == INT32_MIN` occurred in exactly
one lane structurally locked to `b == low_b`. In the two parametrizations that
lane paired `INT32_MIN` with `b = 1` (below the threshold, quotient never
collapses) or with `b == INT32_MIN` (safe by *equality*: `r` and `b` share the
bit pattern, so `v_elseif(r >= b)` holds under any lowering). The LLK harness
could not help either: it sweeps only positive operands below `2**24` because
its sign-magnitude Dst pack path cannot round-trip negatives.

---

## 4. The fix

### 4.1 Division kernels (WH + BH) — `ckernel_sfpu_div_int32_floor.h`

The working patch keeps the existing idiom and corrects both the value and the
sign of the residual:

```cpp
sfpi::vInt r = a - qb;
// Shift before conversion so the valid magnitude 2**31 is representable as
// a positive sign-magnitude integer.
sfpi::vFloat r_f = sfpi::convert<sfpi::vFloat>(sfpi::abs(r) >> 1, sfpi::RoundMode::Nearest);
r_f = sfpi::addexp(r_f, 1 /* delta */);
```

- Dropping the low bit via `abs(r) >> 1` + `addexp` makes the magnitude `2**31`
  representable as a positive sign-magnitude integer; it adds at most `1/|b|` to
  the correction error, which the ~21-bit (WH) / ~22-bit (BH) Halley-refined
  reciprocal plus the single final adjustment can absorb. The error budget is
  deliberately documented in the source, with a note that the remainder kernels
  must **not** assume the same budget (they use a less accurate reciprocal and
  retain the low bit — see the Blackhole counterexample in §4.2).

Sign handling — a correction applies in the wrong direction only when a negative
residual is *real*; when `q == 0` (the collapse case), `r == INT32_MIN` is the
valid positive magnitude `2**31`:

```cpp
sfpi::vInt cor = correction;
v_if(r < 0 && q != 0) {
    tmp = -tmp;
    cor = -cor;
}
v_endif;
q = cor + q;
r -= tmp;
```

The final ±1 fixup is rewritten to reuse one subtraction for both the comparison
and the adjusted result (`r_minus_b = r - b; v_if(r < 0) { r += b; }
v_elseif(r_minus_b >= 0) { r = r_minus_b; }`), and the old `(r - 1) < 0`
`INT_MIN` trap is gone because the corrected remainder can no longer be
`INT32_MIN`.

The correction is a `vUInt16`, so it must stay under 65536. When the guard fires,
`correction ~= 2**31 / |b|`, and the guard can only fire for `|b| >= 2**21`
(WH) / `2**22` (BH), bounding it at 1024 / 512 — a factor of 64 of headroom.

Both kernel files also switch the per-tile loop wrappers from `inline` to
`sfpi_inline` so the inlined reciprocal callbacks do not make SFPI outline the
loop and lose constant tile indices (this is what fixed the register spills seen
in full LTO builds).

### 4.2 Remainder and fmod kernels

`ckernel_sfpu_binary_remainder.h` (both architectures) is reworked:

- The numerator's sign-magnitude repair is parameterised with a new template
  flag `numerator_can_be_int_min` (default `true`). The UINT32 range-reduced
  callers pass `false`, which skips the numerator repair and rules out the
  positive `2**31` residual; a **negative** `INT32_MIN` residual from an
  overshooting quotient approximation is still handled independently.
- The residual conversion gains the same `r_f < 0.0f` → `TWO_POW_31` repair as
  the division kernels. It deliberately does **not** drop the low bit
  (`convert(abs(r) >> 1) + addexp`): combined with the less accurate
  reciprocal, the final adjustment can be insufficient. Documented example:
  `-2140947629 % -1` returned `-1` instead of `0` on Blackhole with the
  low-bit-dropping variant.
- The correction sign test becomes `v_if(r < 0 && q != 0) { tmp = -tmp; }` so
  the `q == 0` / `INT32_MIN` residue is not mis-negated.
- The final adjustment reuses `r_minus_b = r - b` and drops the `(r - 1) < 0`
  trap.
- The reciprocal is hoisted into a scheduled callback
  (`unsigned_remainder_recip_scheduled`) so the tensor path fills the
  reciprocal's dependency slots with independent numerator work while the scalar
  path keeps its loop-invariant reciprocal.
- Remainder sign handling is restructured: first form the truncating remainder,
  then adjust to the divisor's sign
  (`v_if(a < 0) { r = -r; }` then `v_if(r != 0 && sign < 0) { r += b; }`).
- The scalar `calculate_remainder_uint32_scalar` and the binary remainder/fmod
  loop wrappers use `sfpi_inline` (register-pressure fix in LTO builds).

`ckernel_sfpu_binary_fmod.h` and `ckernel_sfpu_remainder.h` (both
architectures) follow the same pattern, including the `numerator_can_be_int_min`
flag and the `sfpi_inline` loop wrappers.

### 4.3 Scalar dispatch and type promotion — `binary_composite_op.cpp`

The Python-level `remainder`, `fmod`, and `div` overloads now dispatch on the
scalar's **type**, not its value:

- `div(int32_tensor, <float scalar>, rounding_mode=...)` promotes the int32
  tensor to FLOAT32 **before** division/rounding via the new
  `promote_int32_scalar_input` helper, so even integral floats like `2.0` take
  the FP32 path (an integer scalar `2` keeps exact INT32 division). Without
  this, `binary_ng` truncated the floating divisor to an integer.
- `remainder` / `fmod` with a float scalar on an int32 tensor promote the input
  to FLOAT32 and route through the unary fast path, supporting TILE and
  ROW_MAJOR layouts, sharded and interleaved memory configs, optional
  preallocated outputs (with FP32/BF16/INT32 output typecasts, fusing the BF16
  conversion into the unary pass), sub-core grids, and sub-device dispatch.
- A `resolve_sub_device_workers` helper maps `sub_device_id` to the worker
  `CoreRangeSet`, and `restore_scalar_output_layout` converts the result back to
  the input layout after promotion (unless a user memory config says otherwise).
- Output typecast restrictions are preserved and turned into explicit
  `validate_scalar_typecast` checks ("...on a restricted grid requires a tiled
  interleaved tensor"; "does not support row-major sharded tensors"; "Optional
  output tensor with Row Major input is not supported").
- The int32 + float-scalar promotion path supports `sub_device_id`, keeping all
  promotion, arithmetic, and layout conversion on the requested sub-device
  workers.

### 4.4 Public API docs — `binary_nanobind.cpp`

- New shared note `kInt32FloatScalarPromotionNote` is appended to the `div`,
  `remainder`, and `fmod` bindings: *"An INT32 tensor with a floating-point
  scalar is promoted to FLOAT32 before computation, including integral-valued
  floats such as `2.0`. The default output dtype is FLOAT32. Use an integer
  scalar (for example, `2` instead of `2.0`) to retain integer-scalar
  semantics."*
- `kDivFastApproxPostNote` is re-scoped: `floor`/`trunc` on INT32 now names
  division by zero and `INT32_MIN / -1` as undefined regardless of
  `fast_and_approximate_mode`; the "properly handles division by zero" claim now
  applies only to floating-point division (including promoted INT32 inputs).

---

## 5. Regression tests

New tests (all parameterised over both architectures via the test device):

- `test_div_int32_min_rounding_modes` — `a = INT32_MIN` against divisors around
  both thresholds (`2**21 - 1/0/+1`, `2**22 - 1/0/+1`, both signs), the #51476
  empirical divisor `239823930`, and signed-format endpoints; tensor-tensor and
  tensor-scalar; both `trunc` and `floor`.
- `test_div_int32_odd_residuals` — odd numerators near the signed-format
  endpoints, the empirical remainder counterexample, and zero, crossed with
  small divisors and divisors straddling the WH/BH coarse-quotient steps.
- `test_binary_remainder_fmod_int32_min` — `a = INT32_MIN` (plus the
  `-2140947629 / -1` BH counterexample) against the threshold divisors and
  signed-format endpoints.
- `test_binary_remainder_fmod_int32_odd_residuals` — odd-numerator windows with
  small divisors and step-straddling divisors.
- `test_binary_remainder_fmod_int32_sign_adjustment` — all operand sign
  combinations, zero remainders, and `INT32_MIN` divisors, in both layouts.
- `test_binary_remainder_fmod_int32_scalar_layout_and_extreme_values` —
  tensor-scalar across layouts and the extreme divisor set.
- Float-scalar promotion tests for remainder/fmod/div: TILE + ROW_MAJOR,
  sub-core grids, sub-devices, sharded inputs (HEIGHT/WIDTH/BLOCK), preallocated
  outputs and output dtypes (FP32/BF16/INT32), non-finite scalars, and the
  explicit guards for unsupported output sharding. `test_div_int32_integer_and_
  float_scalar_remain_distinct` pins the type-based dispatch policy
  (`div(t, 2)` → int32 exact; `div(t, 2.0)` → promoted FP32).
- `test_binary_remainder_uint32_range_reduction_thresholds` — regression for the
  UINT32 path that shares `compute_unsigned_remainder_int32<false>`.
- `test_remainder_mixed_float_output` — mixed FP32 outputs for BF16 inputs
  retain precision and unary layout/grid support.

Goldens are computed with the tensor widened to int64 where PyTorch's int32
`INT_MIN % -1` trap would otherwise fire (the mathematical remainder is
representable).

---

## 6. Verification

### 6.1 Correctness

Emulated instruction-level verification for `a = INT32_MIN` against 20,492
divisors × {trunc, floor} = 40,984 results per platform/model combination:

| patch                  | WH wrong | BH wrong | worst abs err            |
|------------------------|----------|----------|--------------------------|
| current                | 12711    | 12367    | 1023 (WH), 511 (BH)      |
| clamp only             | 24608    | 24264    | **2048** (WH), 1024 (BH) |
| clamp + sign           | **0**    | **0**    | **0**                    |

A wider 699,990-divisor sweep (both signs, both threshold neighbourhoods ±5000,
all `2**e + d`, 350k uniform random) on Wormhole: 480,151 wrong today with
smallest failing divisor exactly `2**21`; **0 wrong** with the fix.

### 6.2 Neutrality

On a regression corpus of 190,320 results (exhaustive `|a|,|b| <= 90`, 30,000
random full-range pairs, all `±2**e + d` cross products), the fix changes **no**
result that does not involve `INT32_MIN`, on either platform.

### 6.3 Performance (no spills, no regression)

Measured cycles/row on device (lower is better):

| Architecture | Operation | Before | After |
|--------------|-----------|:------:|:-----:|
| Blackhole    | trunc div | 60 | **55** |
| Blackhole    | floor div | 67 | **60** |
| Blackhole    | remainder | 71 | **60** |
| Blackhole    | fmod      | 57 | **54** |
| Wormhole     | trunc div | 104 | **100** |
| Wormhole     | floor div | 111 | **105** |
| Wormhole     | remainder | 123 | **111** |
| Wormhole     | fmod      | 109 | **104** |

The `sfpi_inline` loop wrappers specifically fix register spills observed in
full LTO builds (see commit "Fix Wormhole division register spills in LTO
builds").

---

## 7. Acceptance criteria mapping

| Criterion | How it is satisfied |
|-----------|--------------------|
| `ttnn.div` int32 `trunc`/`floor` returns reference result for `INT32_MIN` on WH and BH, except `b = 0` and `INT32_MIN / -1` | §4.1 residual shift-before-conversion + `r < 0 && q != 0` sign guard; §6.1 zero failures |
| Residual magnitude **and** sign handled (value-only clamp insufficient) | §3, §4.1; §6.1 shows clamp-only is worse |
| Tensor remainder/fmod handle `INT32_MIN` edge cases | §4.2 `numerator_can_be_int_min` + residual repair + sign restructure |
| Integer tensor + integer scalar → exact integer semantics | §4.3 dispatch on scalar type; `div(t, 2)` stays int32 |
| Integer tensor + floating-point scalar → FP32 promotion | §4.3 `promote_int32_scalar_input`; `div(t, 2.0)` promotes |
| WH and BH agree on the supported input set | identical guard/sign pattern in both kernel families; §6.1 both report 0 wrong |
| Regression tests: tensor-tensor + tensor-scalar, both rounding modes, both archs, ±divisors, threshold neighbourhoods | §5 |
| No change outside affected edge cases; no spills / no unapproved perf regression | §6.2 neutrality; §6.3 faster + no spills |

---

## 8. References

- [Issue #55502](https://github.com/tenstorrent/tt-metal/issues/55502) — the bounty.
- [Issue #51476](https://github.com/tenstorrent/tt-metal/issues/51476) — the original investigation and reproducer.
- [PR #55506](https://github.com/tenstorrent/tt-metal/pull/55506) — the fix, merged into `main` as `7a0718b`.
- Related prior art: #33241 / #33398 (the original `$10000` full-range int32 div bounty), #33334 (`-0.0f` conversion bug), #20852 (SFPABS integer overflow), #48763 (WH/BH int32 div divergence).