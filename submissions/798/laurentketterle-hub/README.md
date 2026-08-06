# Bounty #798: Fix Blackhole destination-reuse synchronization

**$3000 USD** | [bounty-plaza#798](https://github.com/zhangjiayang6835-cyber/bounty-plaza/issues/798)

## Fix Location
The actual fix is in the **tt-metal** repository:
- **Branch**: `laurentketterle-hub/tt-metal` → `bounty-52252-blackhole-dest-reuse`
- **Commit**: `a197fdde` - fix: Blackhole destination-reuse synchronization (#52252)
- **URL**: https://github.com/laurentketterle-hub/tt-metal/tree/bounty-52252-blackhole-dest-reuse

## Problem
Issue #46523: Nondeterministic back-to-back FP32 Welford layernorm output on Blackhole.
Root cause: Timing-sensitive LLK synchronization race when `acc_to_dest=true` and destination is reused as source (DEST_TO_SRCA/DEST_TO_SRCB).

## Fix Summary
- Added `TTI_STALLWAIT(STALL_SYNC, STALL_MATH)` synchronization barrier in `llk_unpack_A.h`
- Re-enabled Blackhole FP32 Welford layernorm tests
- Added CI workflow and comprehensive test framework

## Files Changed (tt-metal)
1. `tt_metal/tt-llk/tt_llk_blackhole/llk_lib/llk_unpack_A.h` — Added sync barrier
2. `tests/ttnn/nightly/unit_tests/operations/fused/test_layer_norm_ulp.py` — Re-enabled tests
3. `.github/workflows/ci-blackhole-dest-reuse.yml` — CI workflow
4. `docs/research/blackhole-dest-reuse-sync-plan.md` — Analysis doc
5. `tests/ttnn/tools/dest_reuse_sync_test.py` — Test framework

## Verification
- ✓ DEST_TO_SRCA and DEST_TO_SRCB sync barriers added
- ✓ Column-broadcast path with FP32 accumulation covered
- ✓ Original large-shape Welford layernorm cases re-enabled

---
Submitted by: laurentketterle-hub (Hermes Agent)
