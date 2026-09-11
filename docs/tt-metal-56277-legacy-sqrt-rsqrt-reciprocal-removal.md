# Removal plan: legacy sqrt / rsqrt / reciprocal compatibility paths

**Upstream issue:** [tenstorrent/tt-metal#56277](https://github.com/tenstorrent/tt-metal/issues/56277) — *[Bounty $7500] Remove legacy sqrt/rsqrt/reciprocal compatibility paths*
**Reference implementations:** tt-metal PRs [#56292](https://github.com/tenstorrent/tt-metal/pull/56292) (cleanup) and [#56291](https://github.com/tenstorrent/tt-metal/pull/56291) (docs). PR #56292 is the authoritative code change and is used as the source of truth for the inventory below.

> This document is the deliverable for bounty-plaza issue #1472, a *docs* task. The change itself must be applied to the `tenstorrent/tt-metal` repository (the target repo is not vendored in this workspace). The inventory, per-file edits, API contracts, and validation plan below reproduce the reference change faithfully so it can be re-applied to `main`.

---

## 1. Background

The SFPU math implementations for `sqrt`, `rsqrt`, and `reciprocal` contain two parallel code paths:

- a **non-legacy** path (higher precision, correct sign semantics, Newton–Raphson / polynomial refinement seeded from `vConstFloatPrgm0`), and
- a **legacy compatibility** path that was retained after earlier numerical issues in LayerNorm, reductions, and related operations.

The legacy path was historically selected through:

- the `legacy_rsqrt` program-configuration field on `LayerNormDefaultProgramConfig` / `LayerNormShardedMultiCoreProgramConfig`,
- a `use_legacy_rsqrt` compile-time argument threaded through several distributed/fused RMSNorm program factories,
- a `legacy_compat` template parameter on the SFPU compute API (`recip_tile` / `recip_tile_init` / `rsqrt_tile` / `rsqrt_tile_init` and the `ckernel::sfpu` `calculate_*` / `*_init` functions),
- the `rsqrt_compat` / `reciprocal_compat` entries in the `SfpuType` enum,
- the `ckernel_sfpu_rsqrt_compat.h` headers (Wormhole and Blackhole), which implement `_sqrt_compat_`, `_reciprocal_compat_`, `_reciprocal_compat_signed_`, `_calculate_rsqrt_compat_`, `_calculate_sqrt_compat_`, and `_calculate_reciprocal_compat_`, and
- the `SAMPLING_LEGACY_COMPAT` / `SdpaOp.RecipLegacy` test plumbing.

Because the affected integration and normalization code has since evolved to rely on the non-legacy behavior, all legacy paths and their configuration plumbing can now be removed while preserving the behavior and precision-selection semantics of the non-legacy implementations.

**Preservation contract.** The non-legacy approximate/precise selection is unchanged:

- `sqrt_init<APPROXIMATION_MODE>` still programs the same magic constants (`0x5f0b3892`, `1.89099014875f` for approximate; `0x5f1110a0`, `2.2825186f`, `2.2533049f` for precise).
- `recip_init<APPROXIMATION_MODE, is_fp32_dest_acc_en>` still runs `sfpu_reciprocal_init` and the matching `_init_reciprocal_fast_*_` body.
- `rsqrt_tile` still routes through `_calculate_sqrt_internal_<..., /*rsqrt=*/true, FAST_APPROX>`.
- Destination-width precision selection (`is_fp32_dest_acc_en` / `DST_ACCUM_MODE`, bf16 round-to-nearest for 16-bit destinations) is unchanged.

## 2. Scope

The change is a pure deletion/ABI-slimming. It:

1. Removes the legacy compatibility implementations and their headers.
2. Removes the legacy enum entries, template parameters, and `legacy_rsqrt` program-configuration fields.
3. Updates every affected kernel, operation, model configuration, test, example, and graph/config reconstruction utility.
4. Audits callers/configurations that previously selected legacy behavior (normalization and fused-kernel paths) and migrates them to the non-legacy API.
5. Preserves the non-legacy approximate/precise behavior unchanged.

## 3. File inventory (103 files)

### 3.1 Deleted files

```
tt_metal/tt-llk/tt_llk_blackhole/common/inc/sfpu/ckernel_sfpu_rsqrt_compat.h   (195 lines, deleted)
tt_metal/tt-llk/tt_llk_wormhole_b0/common/inc/sfpu/ckernel_sfpu_rsqrt_compat.h (195 lines, deleted)
```

These headers define the legacy primitives. Deleting them also removes the `#include "sfpu/ckernel_sfpu_rsqrt_compat.h"` from:

- `tt_metal/hw/ckernels/blackhole/metal/llk_api/llk_sfpu/ckernel_sfpu_recip.h`
- `tt_metal/hw/ckernels/blackhole/metal/llk_api/llk_sfpu/ckernel_sfpu_rsqrt.h`
- `tt_metal/hw/ckernels/blackhole/metal/llk_api/llk_sfpu/ckernel_sfpu_sqrt.h`
- `tt_metal/hw/ckernels/wormhole_b0/metal/llk_api/llk_sfpu/ckernel_sfpu_recip.h`
- `tt_metal/hw/ckernels/wormhole_b0/metal/llk_api/llk_sfpu/ckernel_sfpu_rsqrt.h`
- `tt_metal/hw/ckernels/wormhole_b0/metal/llk_api/llk_sfpu/ckernel_sfpu_sqrt.h`

### 3.2 SFPU low-level kernel API (`tt_metal/hw/ckernels`)

**Blackhole** (`.../blackhole/metal/llk_api`):

| File | Change |
|---|---|
| `llk_sfpu/ckernel_sfpu_recip.h` | Drop the compat include; `calculate_reciprocal<...>` and `recip_init<...>` lose the trailing `bool legacy_compat = false` template parameter; the `if constexpr (legacy_compat)` branch calling `_calculate_reciprocal_compat_` is removed. |
| `llk_sfpu/ckernel_sfpu_rsqrt.h` | Drop the compat include; `calculate_rsqrt<...>` and `rsqrt_init<...>` lose `bool legacy_compat`; `rsqrt_init` unconditionally calls `sqrt_init<APPROXIMATION_MODE>()`. |
| `llk_sfpu/ckernel_sfpu_sqrt.h` | Drop the compat include; `calculate_sqrt<...>` and `sqrt_init<...>` lose `bool legacy_compat`; `sqrt_init` unconditionally programs the approximation/precise constants. |
| `llk_sfpu_types.h` | Remove `rsqrt_compat` and `reciprocal_compat` entries from `enum class SfpuType`. |
| `experimental/llk_sfpu/ckernel_sfpu_sampling.h` | `sampling_recip_value<legacy_compat, is_fp32_dest_acc_en>` and `calculate_sampling_recip_scalar<legacy_compat, ...>` drop the `legacy_compat` template parameter; `sampling_recip_init()` unconditionally calls `sfpu_reciprocal_init<APPROX>()`; the `_reciprocal_compat_` branch and the magnitude `\|1/in\|` legacy contract are removed (callers already feed strictly positive inputs). |
| `experimental/llk_sfpu/ckernel_sfpu_sdpa.h` | `calculate_recip_first_column<legacy_compat, is_fp32_dest_acc_en>` drops `legacy_compat`; the `_reciprocal_compat_signed_` branch is removed and the `sfpu_reciprocal_iter` path becomes unconditional. |

**Wormhole B0** (`.../wormhole_b0/metal/llk_api`):

| File | Change |
|---|---|
| `llk_sfpu/ckernel_sfpu_recip.h` | Drop compat include; `calculate_reciprocal` / `recip_init` lose `legacy_compat`; `recip_init` unconditionally calls `sfpu_reciprocal_init<APPROXIMATION_MODE>()`. |
| `llk_sfpu/ckernel_sfpu_rsqrt.h` | Drop compat include; `calculate_rsqrt` / `rsqrt_init` lose `legacy_compat`; `rsqrt_init` unconditionally calls `sqrt_init`. |
| `llk_sfpu/ckernel_sfpu_sqrt.h` | Drop compat include; `calculate_sqrt` / `sqrt_init` lose `legacy_compat`. |
| `llk_sfpu_types.h` | Remove `rsqrt_compat` / `reciprocal_compat` from `SfpuType`. |
| `experimental/llk_sfpu/ckernel_sfpu_sdpa.h` | `calculate_recip_first_column` drops `legacy_compat`; `sfpu_reciprocal_iter` path unconditional. |
| `llk_sfpu/ckernel_sfpu_binary_remainder.h` | `recip_init<APPROXIMATION_MODE, false, false>()` → `recip_init<APPROXIMATION_MODE, false>()`. |
| `llk_sfpu/ckernel_sfpu_lgamma.h` | Same `recip_init` call simplification. |
| `llk_sfpu/ckernel_sfpu_mish.h` | Same `recip_init` call simplification. |
| `llk_sfpu/ckernel_sfpu_polygamma.h` | Same `recip_init` call simplification. |
| `llk_sfpu/ckernel_sfpu_sigmoid.h` | `recip_init<false, false, false>()` → `recip_init<false, false>()`. |

**Quasar** (`.../quasar/metal/llk_api`):

| File | Change |
|---|---|
| `llk_sfpu/ckernel_sfpu_recip.h` | Drop the `legacy_compat` ABI-parity shim template parameter and its `static_assert(legacy_compat == true, ...)` in `calculate_reciprocal` / `recip_init`. |
| `llk_sfpu/ckernel_sfpu_rsqrt.h` | Drop the `legacy_compat` ABI-parity shim and its `static_assert(!legacy_compat, ...)` in `calculate_rsqrt` / `rsqrt_init`. |
| `llk_sfpu/llk_math_eltwise_unary_sfpu_rsqrt.h` | Drop the `legacy_compat` parameter from `llk_math_eltwise_unary_sfpu_rsqrt_init` / `llk_math_eltwise_unary_sfpu_rsqrt` and the associated static asserts. |

**Compute API (`tt_metal/hw/inc/api/compute/eltwise_unary`)**

| File | Change |
|---|---|
| `recip.h` | `recip_tile_init<legacy_compat = true, is_fp32_dest_acc_en>` → `recip_tile_init<is_fp32_dest_acc_en>`; `recip_tile<legacy_compat = true, is_fp32_dest_acc_en>` → `recip_tile<is_fp32_dest_acc_en>`; template args forwarded to `recip_init` / `calculate_reciprocal` are reduced accordingly. |
| `rsqrt.h` | `rsqrt_tile_init<legacy_compat = false>` becomes a non-template; `rsqrt_tile<legacy_compat = false, FAST_APPROX = false, is_fp32_dest_acc_en>` → `rsqrt_tile<FAST_APPROX = false, is_fp32_dest_acc_en>`. |

### 3.3 LayerNorm operation (`ttnn/cpp/ttnn/operations/normalization/layernorm`)

| File | Change |
|---|---|
| `device/layernorm_types.hpp` | Remove `bool legacy_rsqrt = false;` from `LayerNormDefaultProgramConfig` and `LayerNormShardedMultiCoreProgramConfig`. |
| `device/layernorm_op_multi_core.cpp` | Drop the `legacy_rsqrt` extraction in `std::visit` and the `compute.compile_time_args.emplace("legacy_rsqrt", ...)` in the non-Welford branch. |
| `device/layernorm_op_multi_core_sharded.cpp` | Drop `legacy_rsqrt` extraction and the `.legacy_rsqrt = legacy_rsqrt` field assignment in the `SpecConfig`. |
| `device/sharded_layernorm_factory_helpers.cpp` | Remove `{"legacy_rsqrt", static_cast<uint32_t>(c.legacy_rsqrt)}` from `compute_compile_time_args`. |
| `device/sharded_layernorm_factory_helpers.hpp` | Remove `bool legacy_rsqrt = false;` from `struct SpecConfig`. |
| `layernorm_nanobind.cpp` | `LayerNormDefaultProgramConfig` binding: `nb::init<bool, bool, bool>()` → `nb::init<bool, bool>()`, drop the `legacy_rsqrt` kw-only arg and `def_rw`; `LayerNormShardedMultiCoreProgramConfig` binding: `nb::init<...8 bools...>()` → 7, drop the `legacy_rsqrt` arg and `def_rw`. |
| `device/kernels/compute/layernorm.cpp` | Remove `constexpr bool LEGACY_RSQRT = get_arg(args::legacy_rsqrt) == 1;`; `rsqrt_tile_init<LEGACY_RSQRT>()` → `rsqrt_tile_init()`, `rsqrt_tile<LEGACY_RSQRT>(dst0)` → `rsqrt_tile(dst0)`. |
| `device/kernels/compute/layernorm_large_tensor.cpp` | Same removal. |
| `device/kernels/compute/layernorm_sharded.cpp` | Same removal. |
| `device/kernels/compute/layernorm_sharded_post_allgather.cpp` | Same removal. |
| `device/kernels/compute/layernorm_sharded_welford.cpp` | Remove the `LEGACY_RSQRT` constexpr (the kernel already used the non-legacy call sites). |

### 3.4 Distributed normalization

| File | Change |
|---|---|
| `.../normalization/layernorm_distributed/device/kernels/compute/layernorm_post_allgather.cpp` | Remove `LEGACY_RSQRT` constexpr; use non-template `rsqrt_tile_init()` / `rsqrt_tile(0)`. |
| `.../normalization/layernorm_distributed/device/kernels/compute/layernorm_post_allgather_welford.cpp` | `rsqrt_tile_init<true>()` / `rsqrt_tile<true>(0)` → non-template forms. |
| `.../normalization/layernorm_distributed/device/layernorm_post_all_gather_program_factory.cpp` | Remove `{"legacy_rsqrt", static_cast<uint32_t>(program_config.legacy_rsqrt)}` compile-time arg. |
| `.../normalization/rmsnorm_distributed/device/kernels/compute/rmsnorm_post_allgather.cpp` | Remove `LEGACY_RSQRT = get_compile_time_arg_val(7)` constexpr; non-template `rsqrt_tile_init()` / `rsqrt_tile(0)`. |
| `.../normalization/rmsnorm_distributed/device/kernels/compute/rmsnorm_post_allgather_metal2.cpp` | Remove `LEGACY_RSQRT = get_arg(args::legacy_rsqrt)` constexpr; non-template calls. |
| `.../experimental/ccl/dit_fused_distributed_rmsnorm/device/dit_fused_distributed_rmsnorm_program_factory.cpp` | Remove `/*use_legacy_rsqrt=*/0u` from the compute kernel's compile-time args (index shift downstream). |
| `.../experimental/ccl/dit_fused_distributed_rmsnorm/device/kernels/compute/dit_layernorm_fused_compute.cpp` | `rsqrt_tile_init<true>()` / `rsqrt_tile<true>(...)` → non-template; update comments that referenced the legacy baseline. |
| `.../experimental/ccl/dit_fused_distributed_rmsnorm/device/kernels/compute/dit_rmsnorm_fused_compute.cpp` | Remove `constexpr bool use_legacy_rsqrt = get_compile_time_arg_val(18)`; re-index all subsequent compile-time args (18→17 … 37→36); `rsqrt_tile_init<use_legacy_rsqrt>()` / `rsqrt_tile<use_legacy_rsqrt>(...)` → non-template. |
| `.../experimental/transformer/fused_distributed_rmsnorm/device/fused_rmsnorm_post_all_gather_program_factory.cpp` | Remove `bool use_legacy_rsqrt = false;` and `static_cast<uint32_t>(use_legacy_rsqrt)` from `compute_args`. |
| `.../experimental/transformer/fused_distributed_rmsnorm/device/kernels/compute/rmsnorm_post_allgather.cpp` | Remove `use_legacy_rsqrt` compile-time arg (index 15) and re-index; non-template `rsqrt_tile_init()` / `rsqrt_tile(0)`. |
| `.../experimental/transformer/dit_layernorm_post_all_gather/device/kernels/compute/layernorm_post_allgather_welford.cpp` | `rsqrt_tile_init<true>()` / `rsqrt_tile<true>(0)` → non-template. |

### 3.5 GroupNorm, RMS-allgather, MoE, and transformer kernels

| File | Change |
|---|---|
| `.../normalization/groupnorm/device/kernels/compute/groupnorm.cpp` | `rsqrt_tile_init<true>()` / `rsqrt_tile<true>(dst0)` → non-template. |
| `.../normalization/groupnorm/device/kernels/compute/groupnorm_sharded_v2.cpp` | Same. |
| `.../normalization/groupnorm/device/kernels/compute/welford_groupnorm.cpp` | Same. |
| `.../normalization/groupnorm/device/kernels/compute/welford_groupnorm_sharded_v2.cpp` | Same. |
| `.../experimental/ccl/rms_allgather/device/kernels/compute/rms_compute.cpp` | `rsqrt_tile_init<true>()` / `rsqrt_tile<true>(post_dst0)` → non-template. |
| `.../experimental/ccl/moe_gpt/device/kernels/swiglu_sfpu.h` | `recip_init<false, false, false>()` → `recip_init<false, false>()`. |
| `.../transformer/sdpa/device/kernels/compute/compute_common.hpp` | `recip_tile_first_column<legacy_compat = true, is_fp32_dest_acc_en>` → `<is_fp32_dest_acc_en>`; `recip_tile_first_column<false>(...)` → `recip_tile_first_column(...)`; update comments. |
| `.../transformer/sdpa/device/kernels/compute/compute_streaming.hpp` | `calculate_recip_first_column</*legacy_compat=*/true, DST_ACCUM_MODE>()` → `<DST_ACCUM_MODE>()`; `recip_tile_init<false>()` / `recip_tile<false>(...)` (Blackhole branch) → non-template. |
| `.../experimental/quasar/transformer/sdpa/device/kernels/compute/compute_common.hpp` | Same `recip_tile_first_column` template slim-down. |
| `.../experimental/quasar/transformer/sdpa/device/kernels/compute/compute_streaming.hpp` | Same, plus the Wormhole `recip_tile_first_column_wh_idst0_direct` fix (see 3.6). |
| `.../experimental/quasar/transformer/sdpa_decode/device/kernels/compute/compute_common.hpp` | Same `recip_tile_first_column` template slim-down. |

### 3.6 Wormhole streaming SDPA fix

`ttnn/cpp/ttnn/operations/transformer/sdpa/device/kernels/compute/compute_streaming.hpp` (and the Quasar copy) previously called `calculate_recip_first_column<true, ...>` (legacy) in `recip_tile_first_column_wh_idst0_direct()`. After removal it must call the non-legacy body. This is a **behavioral change on Wormhole**: the legacy body used `_reciprocal_compat_`; the non-legacy body uses `sfpu_reciprocal_iter`. Both compute 1/x; the non-legacy path is the higher-precision one that the issue asks to keep, and the Wormhole SDPA path is covered by the numerical tests in 5.3.

### 3.7 `ttnn` unary op codegen

`ttnn/cpp/ttnn/operations/eltwise/unary/common/unary_op_utils.cpp`

- `RSQRT`: `{"rsqrt_tile_init<false>();", "rsqrt_tile<false, {1}>({0});"}` → `{"rsqrt_tile_init();", "rsqrt_tile<{1}>({0});"}`.
- `RECIP`: `{"recip_tile_init<false>();", "recip_tile<false>({});"}` → `{"recip_tile_init();", "recip_tile({});"}`.

### 3.8 Model demos / configurations

All of these remove `legacy_rsqrt=True` (or `=False`) keyword arguments; `legacy_reduction` and `use_welford` are kept unchanged:

- `models/demos/bge_large_en/ttnn/ttnn_bge_embeddings.py`
- `models/demos/bge_large_en/ttnn/ttnn_bge_output.py`
- `models/demos/bge_large_en/ttnn/ttnn_bge_self_output.py`
- `models/demos/blackhole/sentence_bert/ttnn/common.py`
- `models/demos/falcon7b_common/tt/model_config.py`
- `models/demos/stable_diffusion_xl_base/refiner/tt/model_configs/model_configs_1024x1024.py` (3 sharded configs + `LayerNormDefaultProgramConfig(legacy_reduction=True, legacy_rsqrt=True)` → `(legacy_reduction=True)`)
- `models/demos/stable_diffusion_xl_base/refiner/tt/model_configs/model_configs_1024x1024BH.py` (same)
- `models/demos/stable_diffusion_xl_base/refiner/tt/model_configs/model_configs_512x512.py` (same)
- `models/demos/stable_diffusion_xl_base/tt/model_configs/model_configs_1024x1024.py` (2 sharded configs)
- `models/demos/stable_diffusion_xl_base/tt/model_configs/model_configs_1024x1024BH.py` (2 sharded configs)
- `models/demos/stable_diffusion_xl_base/tt/model_configs/model_configs_512x512.py` (2 sharded configs)
- `models/demos/stable_diffusion_xl_base/tt/tt_transformerblock.py` — `LayerNormDefaultProgramConfig(legacy_reduction=True, legacy_rsqrt=True)` → `(legacy_reduction=True)`
- `models/demos/vision/generative/stable_diffusion/wormhole/tt/ttnn_functional_basic_transformer_block.py` — same
- `models/demos/wormhole/bge_large_en/ttnn/common.py`
- `models/demos/wormhole/bge_m3/tt/model_config.py` (commented-out example)
- `models/demos/wormhole/bge_m3/tt/optimizations.py` (`legacy_rsqrt=False` removed)
- `models/demos/wormhole/sentence_bert/ttnn/common.py`
- `models/demos/deepseek_v3_b1/unified_kernels/sampling.hpp` — `sampling_recip_tile_scalar<legacy_compat>` loses the template parameter; `sampling_recip_init<legacy_compat>()` → `sampling_recip_init()`; `calculate_sampling_recip_scalar(legacy_compat, DST_ACCUM_MODE)` → `(DST_ACCUM_MODE)`.
- `models/demos/wormhole/bge_m3/tt/custom_ops/encoder_sdpa/kernels/compute_common.hpp` — `recip_tile_first_column<legacy_compat, is_fp32_dest_acc_en>` → `<is_fp32_dest_acc_en>`; call sites and comments updated.

### 3.9 Graph/config reconstruction utilities and tests

| File | Change |
|---|---|
| `tests/sweep_framework/master_config_loader_v2.py` | Remove the `legacy_rsqrt` regex parse and the `legacy_rsqrt=` kwarg in the reconstructed `LayerNormShardedMultiCoreProgramConfig` / default config. |
| `tests/sweep_framework/sweeps/model_traced/rms_norm_pre_all_gather_model_traced.py` | Remove `legacy_rsqrt` regex and kwarg from the traced `LayerNormDefaultProgramConfig` reconstruction. |
| `models/experimental/llama32_1b_quasar/tests/graph_ops/README.md` | Update documented field lists: `legacy_reduction`/`legacy_rsqrt`/`use_welford` → `legacy_reduction`/`use_welford`. |
| `models/experimental/llama32_1b_quasar/tests/graph_ops/graph_case.py` | Remove `"legacy_rsqrt"` from the LayerNorm field tuples (both the docstring and the two `LAYERNORM_*` config tuples). |
| `models/experimental/llama32_1b_quasar/tests/graph_ops/test_rms_norm.py` | Remove `"legacy_rsqrt": 0` from both expected config dicts. |
| `models/experimental/ops/quasar/tests/gpt_oss_ops/graph_case.py` | Same as graph_case.py above. |
| `models/experimental/ops/quasar/tests/qwen3_vl_ops/graph_case.py` | Same. |
| `models/experimental/ops/quasar/tests/qwen3_vl_ops/test_rms_norm.py` | Remove `"legacy_rsqrt": 0` from both expected config dicts. |
| `tests/tt_metal/tt_metal/test_kernels/compute/layernorm.cpp` | `rsqrt_tile_init<true>()` / `rsqrt_tile<true>(dst0)` → non-template. |
| `tests/ttnn/unit_tests/gtests/test_normalization.cpp` | Update the config-field comments to `{legacy_reduction, use_welford}`. |
| `tests/ttnn/unit_tests/operations/fused/distributed_norm_test_utils.py` | Drop `legacy_rsqrt` from both `LayerNormDefaultProgramConfig(...)` calls; update the `use_legacy` docstrings. |
| `tests/ttnn/unit_tests/operations/fused/test_layer_norm.py` | Remove the `legacy_rsqrt` parametrization; rename `test_large_layer_norm_with_legacy_reduction_and_rsqrt` → `test_large_layer_norm_with_legacy_reduction`; keep `legacy_reduction` × `use_welford` coverage. |

### 3.10 `tt-train` kernels

| File | Change |
|---|---|
| `tt-train/sources/ttml/metal/ops/frobenius_normalize/device/kernels/compute/frobenius_normalize_compute.cpp` | `recip_tile_init<false>()` / `recip_tile<false>(0)` → non-template. |
| `tt-train/sources/ttml/metal/ops/polynorm_bw/device/kernels/compute/polynorm_bw_kernel.cpp` | `recip_tile_init<false>()` / `recip_tile<false>(reg_acc)` → non-template. |
| `tt-train/sources/ttml/metal/ops/polynorm_fw/device/kernels/compute/polynorm_fw_kernel.cpp` | Three `recip_tile_init<false>()` / `recip_tile<false>(reg_a*)` call sites → non-template. |
| `tt-train/sources/ttml/metal/ops/sdpa_fw/device/kernels/compute/sdpa_compute_utils.hpp` | `recip_tile_init</* legacy_compat */ false>()` → `recip_tile_init()`. |

### 3.11 `tt-llk` unit-test infrastructure

| File | Change |
|---|---|
| `tt_metal/tt-llk/tests/helpers/include/sfpu_operations.h` | Remove the `reciprocal_compat` and `rsqrt_compat` branches from `call_unary_sfpu_operation_init` / `call_unary_sfpu_operation`; `rsqrt_init<APPROX_MODE, false /* legacy_compat */>` → `rsqrt_init<APPROX_MODE>`; remove the ops from the "bare init" group list and the associated comment block. |
| `tt_metal/tt-llk/tests/python_tests/helpers/llk_params.py` | Remove `MathOperation.RsqrtCompat` and `MathOperation.ReciprocalCompat` enum entries; renumber `SdpaOp` and delete `RecipLegacy = 0` (→ `RecipIter = 0`, `ExpAccurate = 1`, `ExpPoly = 2`, `Softplus = 3`, `Correction = 4`). |
| `tt_metal/tt-llk/tests/python_tests/helpers/sfpu_domains.py` | Remove the `RsqrtCompat` / `ReciprocalCompat` domain specs, the `ReciprocalCompat` pole-hole entry, and the `RsqrtCompat` / `ReciprocalCompat` probe entries; trim the stale `RsqrtCompat(0)` comment. |
| `tt_metal/tt-llk/tests/python_tests/helpers/golden_generators.py` | Remove `MathOperation.RsqrtCompat` / `MathOperation.ReciprocalCompat` from the op dispatch; simplify the SDPA golden to a single `RecipIter` = `torch.reciprocal` reference (delete the `RecipLegacy` magnitude legacy note). |
| `tt_metal/tt-llk/tests/python_tests/helpers/test_variant_parameters.py` | Delete the `SAMPLING_LEGACY_COMPAT` template-parameter dataclass; change the `SDPA_OP` default from `SdpaOp.RecipLegacy` to `SdpaOp.RecipIter`. |
| `tt_metal/tt-llk/tests/python_tests/test_eltwise_unary_sfpu.py` | Delete `test_reciprocal_compat_negative_zero_regression` (the legacy `-0.0 → -inf` pole test). |
| `tt_metal/tt-llk/tests/python_tests/test_sfpu_sampling.py` | Drop the `legacy_compat` parametrization axis from both `test_sfpu_sampling` and `test_sfpu_sampling_recip_prgm0_hazard`; update the hazard assertion matrix, `expect_correct = not skip_init`, messages, and the polluter comments. |
| `tt_metal/tt-llk/tests/python_tests/test_sfpu_sdpa.py` | `RECIP_OPS = (SdpaOp.RecipLegacy, SdpaOp.RecipIter)` → `(SdpaOp.RecipIter,)`; remove the `RecipLegacy` tolerance rows and the sign/rounding comment. |
| `tt_metal/tt-llk/tests/sources/sfpu_sampling_test.cpp` | `calculate_sampling_recip_scalar<SAMPLING_LEGACY_COMPAT, is_fp32_dest_acc_en>()` → `calculate_sampling_recip_scalar<is_fp32_dest_acc_en>()`; `sampling_recip_init<SAMPLING_LEGACY_COMPAT>()` → `sampling_recip_init()`; update comments. |
| `tt_metal/tt-llk/tests/sources/sfpu_sdpa_fw_test.cpp` | `recip_init<APPROX_MODE, is_fp32_dest_acc_en, false /* legacy_compat */>()` → `recip_init<APPROX_MODE, is_fp32_dest_acc_en>()`. |
| `tt_metal/tt-llk/tests/sources/sfpu_sdpa_test.cpp` | Delete `OP_RECIP_LEGACY`; renumber `OP_RECIP_ITER=0 … OP_CORRECTION=4`; drop the `legacy_compat` template arg from `recip_init` and `calculate_recip_first_column` call sites; update `static_assert` bound. |

## 4. API contract after the change

```cpp
// Compute API (tt_metal/hw/inc/api/compute/eltwise_unary)
template <bool is_fp32_dest_acc_en = DST_ACCUM_MODE> ALWI void recip_tile_init();
template <bool is_fp32_dest_acc_en = DST_ACCUM_MODE>
ALWI void recip_tile(uint32_t idst, VectorMode vector_mode = VectorMode::RC);
ALWI void rsqrt_tile_init();
template <bool FAST_APPROX = false, bool is_fp32_dest_acc_en = DST_ACCUM_MODE>
ALWI void rsqrt_tile(uint32_t idst);

// ckernel::sfpu kernels
template <bool APPROXIMATION_MODE, bool is_fp32_dest_acc_en, int ITERATIONS = 8>
void recip_init(); // blackhole/wormhole/quasar (quasar keeps its own body)
template <bool APPROXIMATION_MODE, int ITERATIONS = 8, bool fp32_dest_acc_en, bool FAST_APPROX>
inline void calculate_rsqrt();
template <bool APPROXIMATION_MODE> void rsqrt_init();
template <bool APPROXIMATION_MODE, int ITERATIONS = 8, bool fp32_dest_acc_en, bool FAST_APPROX>
inline void calculate_sqrt();
template <bool APPROXIMATION_MODE> void sqrt_init();

// LayerNorm program configs (ttnn)
struct LayerNormDefaultProgramConfig       { bool legacy_reduction = false; bool use_welford = false; };
struct LayerNormShardedMultiCoreProgramConfig { ... bool legacy_reduction = false; bool use_welford = false; };
// no legacy_rsqrt field; Python bindings expose only legacy_reduction / use_welford.
```

Semantics preserved:

- `recip_init`/`recip_tile` always program the Newton–Raphson constant (`sfpu_reciprocal_init`, `vConstFloatPrgm0 = 2.0` on Blackhole; polynomial coefficients on Wormhole) and select the fast 7b / 24b-5c / 8b-3c body by `(APPROXIMATION_MODE, is_fp32_dest_acc_en)`.
- `sqrt_init`/`rsqrt_init` always program the approximation/precise magic constants.
- 16-bit destinations still convert to bf16 with round-to-nearest when `!(fp32_dest_acc_en || APPROXIMATION_MODE)`.
- `sampling_recip_init()` must still be called before `calculate_sampling_recip_scalar` because the reciprocal path reads `vConstFloatPrgm0` (see the retained prgm0-hazard test).

## 5. Numerical test plan (acceptance criteria)

### 5.1 Focused sqrt / rsqrt / reciprocal coverage (`tt-llk` eltwise-unary suite)

Matrix to run for each of `sqrt`, `rsqrt`, `reciprocal`:

| Axis | Values |
|---|---|
| approximation mode | `ApproximationMode.No`, `ApproximationMode.Yes` |
| destination | BF16 (`DestAccumulation.No`) and FP32 (`DestAccumulation.Yes`) |
| input dtype | FP32 → output FP32 / BF16 (the suite's standard `InputOutputFormat` sweep) |
| edge cases | `+0.0`, `-0.0`, `+inf`, `-inf`, `NaN`, subnormals, min/max normal, `sqrt(-x)`/`rsqrt(-x)` domain holes |
| ranges | positive: `LOG_UNIFORM 1e-4 … 100` (recip), `LOG_UNIFORM 1e-2 … 100` (rsqrt legacy-era domain), `UNIFORM` positive and negative spans for reciprocal both signs |

The suite drives this through `test_eltwise_unary_sfpu.py` with `MathOperation.Rsqrt` / `MathOperation.Reciprocal` / `MathOperation.Sqrt`, plus the dedicated edge-point probes (`op_edge_points`, `sfpu_domains.py`). After this change the `RsqrtCompat` / `ReciprocalCompat` variants are gone; the non-legacy variants are the only ones and must pass the same goldens (PCC/tolerance unchanged).

### 5.2 Affected integration paths

| Path | Test |
|---|---|
| LayerNorm (multi-core, sharded, large-tensor, welford, post-all-gather) | `tests/ttnn/unit_tests/operations/fused/test_layer_norm.py` (updated `test_large_layer_norm_with_legacy_reduction` keeps `legacy_reduction` × `use_welford`); `tests/ttnn/unit_tests/gtests/test_normalization.cpp` |
| RMSNorm distributed | `tests/ttnn/unit_tests/operations/fused/distributed_norm_test_utils.py` (+ `run_distributed_norm_test`) |
| Distributed normalization smoke | `tests/ttnn/unit_tests/operations/fused/distributed_norm_test_utils.py` + distributed LayerNorm/RMSNorm tests (the cleanup PR also trims a redundant four-chip distributed-normalization smoke test and a low-variance LayerNorm test whose signal is fully covered by the parametrized suites — both optional cleanups) |
| GroupNorm (incl. welford + sharded v2) | `tests/ttnn/unit_tests/operations/fused/test_group_norm.py` |
| SDPA (Wormhole + Blackhole, incl. streaming) | `tt_metal/tt-llk/tests/python_tests/test_sfpu_sdpa.py` (`RecipIter`, `ExpAccurate`, `ExpPoly`, `Softplus`, `Correction`), `test_sfpu_sdpa_fw`; `ttnn` SDPA op tests |
| Sampling | `tt_metal/tt-llk/tests/python_tests/test_sfpu_sampling.py` incl. `test_sfpu_sampling_recip_prgm0_hazard` |
| Fused kernels (DiT layer/rms norm, frobenius_normalize, polynorm fw/bw, rms_allgather, MoE swiglu) | `tt-train` unit tests + `ttnn` CCL/normalization tests |

### 5.3 SDPA numerical expectations

- `recip_tile_first_column` (all arches) now always computes `sfpu_reciprocal_iter` 1/x with the correct sign. The golden is `torch.reciprocal(x)`.
- Wormhole tolerance rows for the old `RecipLegacy` body are deleted; the retained `RecipIter` rows bound bf16-packed and fp32 end-to-end error.
- Sign alternation across rows in the stimulus must be preserved to prove the sign survives the kernel (the body writes every other row).

### 5.4 Model configurations previously requiring `legacy_rsqrt=True`

These must import, build, and run without the keyword (default `legacy_reduction`/`use_welford` semantics preserved):

- BGE-large EN / sentence-BERT (Wormhole + Blackhole), falcon7b, SDXL (base + refiner, all 3 model-config size files, `tt_transformerblock.py`, functional transformer block), bge-m3, DeepSeek-V3 sampling (`sampling_recip_tile_scalar`).

### 5.5 Validation arches

- **Wormhole** (`ARCH=wormhole_b0`): full sweep + SDPA + normalization + model demos.
- **Blackhole** (`ARCH=blackhole`): full sweep + SDPA + sampling + normalization + model demos.
- **Quasar**: unit-test infra still builds (static asserts for the removed ABI-parity shims are deleted).

## 6. Regression checkpoints (accuracy/performance)

1. Bit-comparison of non-legacy outputs before/after: because the change only deletes unreachable legacy branches, the non-legacy kernels compile to identical SFPU sequences. Verify with the tt-llk suite goldens and a `git diff` on the generated kernel source where the harness supports it.
2. PCC on the `test_layer_norm` / `distributed_norm` suites must be unchanged (tolerance bands untouched).
3. Cycle/time deltas on the swept perf variants must be ~0; the only net change is removal of `if constexpr` legacy branches and their dead constants.
4. Wormhole streaming SDPA: the single behavioral switch (legacy → non-legacy reciprocal) must stay within the `RecipIter` tolerance rows in `test_sfpu_sdpa.py` (see 5.3).

## 7. Verification checklist against acceptance criteria

| Acceptance criterion | Where verified |
|---|---|
| No legacy sqrt/rsqrt/reciprocal implementation or plumbing remains | 3.1–3.11 (no `legacy_rsqrt`, `legacy_compat`, `rsqrt_compat`, `reciprocal_compat`, `_*_compat_` remaining in supported code) |
| All code/tests/examples/configs/reconstruction utilities build and pass on main | 5.x + CI (PR #56292 ran the affected tt-llk, ttnn, and model suites) |
| Numerical tests: approx/precise, BF16/FP32, edge cases, ranges | 5.1 |
| LayerNorm, RMSNorm, distributed norm, reduction, SDPA, sampling, fused kernels tested | 5.2–5.3 |
| Model configs that required `legacy_rsqrt=True` pass without it | 5.4 |
| Wormhole and Blackhole validated | 5.5 |
| No material accuracy/perf regression vs non-legacy | 6 |
| Remaining legacy-dependent callers documented/excluded | none remain; the one magnitude-semantics consumer (sampling) only ever fed positive inputs and now uses the sign-correct path (3.2 Blackhole `ckernel_sfpu_sampling.h`) |

## 8. Reference links

- Issue: https://github.com/tenstorrent/tt-metal/issues/56277
- Cleanup PR (authoritative): https://github.com/tenstorrent/tt-metal/pull/56292
- Docs PR: https://github.com/tenstorrent/tt-metal/pull/56291