# Bounty #765 / upstream tt-metal #52014 submission

Upstream issue: https://github.com/tenstorrent/tt-metal/issues/52014

This submission provides a patch against `tenstorrent/tt-metal` for the SFPU-backed `ttnn.uniform` random path.

No upstream PR has been opened by this submitter; this PR is the bounty-plaza submission. The patch is ready for bounty-plaza/admin review and upstream application.

## What changed

- Mixes explicit user seeds, and random per-core seeds when `seed == 0`, with the per-core index before initializing the SFPU PRNG.
- Avoids invalid/degenerate seed states, including the XNOR-LFSR all-ones lock state.
- Changes the SFPU uniform kernel on both Wormhole and Blackhole to combine two raw PRNG draws, add them for carry nonlinearity, and xorshift-fold bits before FP32 construction. This reduces direct exposure of a single raw LFSR draw.
- Preserves `[from, to)` behavior for narrow FP32 ranges by using `nextafter(to, from)` as the upper rounding guard instead of subtracting a fixed `1e-6`.
- Re-applies input validation on program-cache hits, so dynamic `from`/`to` values cannot bypass validation after `from`/`to`/`seed` were excluded from the program hash.
- Adds regression tests for all-ones seed lock, narrow FP32 ranges, adjacent-sample correlation, distribution mean/std, histogram balance, and low numeric bucket parity.

## Acceptance criteria coverage

- Per-core streams no longer start from adjacent raw seed states: addressed by host-side SplitMix-style per-core seed mixing.
- All-ones XNOR-LFSR lock state: addressed by seed sanitization after mixing.
- Raw single-draw mantissa exposure: improved by two-draw SFPU mixing with integer addition and xorshift folding.
- Narrow FP32 ranges: addressed by replacing fixed epsilon shrink with `nextafter(to, from)`.
- Program cache dynamic args: addressed by runtime-arg override plus cache-hit validation.
- Wormhole and Blackhole: both SFPU rand headers are patched.

## Known validation gaps

- This runner has no Tenstorrent WH/BH device attached and no local `torch`, so full TT hardware pytest and performance benchmarks were not run here.
- The SFPU hot loop is stronger than the old one-draw path, but final acceptance should still include maintainer hardware/statistical review because SFPU instruction choices are constrained and the loop adds extra SFPU work.

## Files in patch

- `ttnn/cpp/ttnn/operations/uniform/device/uniform_program_factory.cpp`
- `ttnn/cpp/ttnn/operations/uniform/device/uniform_device_operation.cpp`
- `ttnn/cpp/ttnn/operations/uniform/device/uniform_device_operation.hpp`
- `tt_metal/hw/ckernels/wormhole_b0/metal/llk_api/llk_sfpu/ckernel_sfpu_rand.h`
- `tt_metal/hw/ckernels/blackhole/metal/llk_api/llk_sfpu/ckernel_sfpu_rand.h`
- `tests/ttnn/nightly/unit_tests/operations/rand/test_uniform.py`

## Apply/check

From a clean `tenstorrent/tt-metal` checkout:

```bash
git apply --check submissions/765/luzijano/tt-metal-sfpu-rng-quality.patch
git apply submissions/765/luzijano/tt-metal-sfpu-rng-quality.patch
python3 -m py_compile tests/ttnn/nightly/unit_tests/operations/rand/test_uniform.py
git diff --check
```

## Local validation available on this runner

- `python3 -m py_compile tests/ttnn/nightly/unit_tests/operations/rand/test_uniform.py` passed.
- `git diff --check` passed.
- Static guard confirmed both SFPU architecture headers contain two-draw mixed RNG logic.
