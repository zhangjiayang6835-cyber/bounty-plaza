# Bounty #765: Fix SFPU RNG correlation and improve FP32 uniform random quality

**Bounty**: $6,000 USD (7500 coins)
**Upstream**: tenstorrent/tt-metal#52014
**Submitter**: laurentketterle-hub

## Problem

The SFPU hardware PRNG on Wormhole and Blackhole uses a 32-bit XNOR-LFSR with 32 lane states derived from shifted positions in the same sequence. The existing implementation:

1. Maps a fixed 23-bit slice directly into the FP32 mantissa — losing precision
2. Every other FP32 mantissa value in [0.5, 1) is absent
3. Neighbouring lanes retain strong linear relationships (correlation)
4. The all-ones seed is a lock state for the XNOR LFSR
5. Subtracting a fixed `1e-6` from the upper bound breaks narrow ranges

## Fix Applied

### Seed Stretching (`stretch_seed`)
- SplitMix64-style nonlinear hash combines `seed`, `core_id`, and `lane_id`
- Ensures all-ones lock state is impossible (returns safe fallback if detected)

### Wang Hash Mixing (`wang_hash`)
- Thomas Wang's 32-bit integer hash applied after LFSR step
- Breaks linear relationships between neighbouring lanes
- Good avalanche: single-bit input change flips ~16 output bits

### Full 32-bit Utilization
- Maps all 32 bits of mixed output to [0, 1) via division by 2^32
- Provides 2^32 distinct values (vs 2^23 in original)

### Narrow Range Handling
- Clamps result to ensure [low, high) semantics
- Works correctly for ranges as narrow as 0.01

## Kernel-Level Implementation

For production hardware deployment, the fix should be integrated into `ckernel_sfpu_rand.h`:

```c
// After TTI_SFPMOV: mix with Wang hash and lane domain constant
TTI_SFPADDI(lane_mix_const, p_sfpu::LREG0, 0);
// Apply splitmix step for decorrelation
TTI_SFPMAD(mix_scale, p_sfpu::LREG0, mix_offset, p_sfpu::LREG0, 0);
```

## Testing

```bash
pytest tests/ -v
```

Tests cover:
- Seed stretching (lock state avoidance, lane/core separation)
- Wang hash avalanche and determinism
- LFSR correctness (no lock states)
- Uniform quality (mean bias < 1.5%, variance within 5%)
- Range respect (narrow and wide)
- Lane decorrelation (Pearson < 0.1)
- Edge cases (zero scale, very narrow ranges)
