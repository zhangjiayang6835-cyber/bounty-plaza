"""Tests for SFPU RNG Decorrelation Fix."""
import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from sfpu_rng_decorrelate import (
    SFPURNG, stretch_seed, wang_hash,
    float_to_bits, bits_to_float, decorrelated_uniform
)

import math
import pytest
from sfpu_rng_decorrelate import (
    SFPURNG, stretch_seed, wang_hash,
    float_to_bits, bits_to_float, decorrelated_uniform
)


class TestSeedStretching:
    def test_all_ones_avoided(self):
        for lane in range(32):
            s = stretch_seed(0xFFFFFFFF, lane_id=lane)
            assert s != 0xFFFFFFFF, f'Lane {lane} returned lock state'
            assert s >= 0 and s < 2**32

    def test_different_lanes_different_seeds(self):
        seeds = {stretch_seed(42, lane_id=i) for i in range(32)}
        assert len(seeds) == 32, f'Only {len(seeds)} unique seeds for 32 lanes'

    def test_different_cores_different_seeds(self):
        s0 = stretch_seed(42, core_id=0)
        s1 = stretch_seed(42, core_id=1)
        assert s0 != s1, 'Same seed for different cores'


class TestWangHash:
    def test_avalanche(self):
        original = wang_hash(0x12345678)
        flipped = wang_hash(0x12345679)
        diff = original ^ flipped
        bit_diff = bin(diff).count('1')
        assert bit_diff >= 12, f'Only {bit_diff} bits differ'

    def test_deterministic(self):
        assert wang_hash(42) == wang_hash(42)


class TestLFSR:
    def test_not_all_ones(self):
        rng = SFPURNG(seed=0xFFFFFFFF)
        states = [rng._lfsr_step(rng.lane_states[0]) for _ in range(100)]
        assert 0xFFFFFFFF not in states


class TestUniformQuality:
    def test_mean_unbiased(self):
        rng = SFPURNG(seed=12345)
        samples = [rng.next_float(i % 32, 0.0, 1.0) for i in range(10000)]
        mean = sum(samples) / len(samples)
        assert abs(mean - 0.5) < 0.015, f'Mean bias {abs(mean-0.5):.4f}'

    def test_variance(self):
        rng = SFPURNG(seed=54321)
        samples = [rng.next_float(i % 32, 0.0, 1.0) for i in range(10000)]
        mean = sum(samples) / len(samples)
        variance = sum((x - mean)**2 for x in samples) / len(samples)
        expected = 1.0/12.0
        assert abs(variance - expected)/expected < 0.05

    def test_range_respected(self):
        rng = SFPURNG(seed=99)
        for _ in range(1000):
            x = rng.next_float(0, -1.5, 3.7)
            assert -1.5 <= x < 3.7

    def test_distinct_values(self):
        rng = SFPURNG(seed=7)
        values = {rng.next_float(i % 32, 0.0, 1.0) for i in range(1000)}
        assert len(values) > 950, f'Only {len(values)} unique out of 1000'


class TestLaneDecorrelation:
    def test_low_correlation(self):
        rng = SFPURNG(seed=42)
        n = 500
        lane0 = [rng.next_float(0, 0.0, 1.0) for _ in range(n)]
        lane1 = [rng.next_float(1, 0.0, 1.0) for _ in range(n)]
        mean0, mean1 = sum(lane0)/n, sum(lane1)/n
        cov = sum((a-mean0)*(b-mean1) for a,b in zip(lane0, lane1))/n
        std0 = math.sqrt(sum((x-mean0)**2 for x in lane0)/n)
        std1 = math.sqrt(sum((x-mean1)**2 for x in lane1)/n)
        corr = cov/(std0*std1) if std0>0 and std1>0 else 1.0
        assert abs(corr) < 0.1, f'Correlation {corr:.4f}'


class TestEdgeCases:
    def test_narrow_range(self):
        rng = SFPURNG(seed=1)
        samples = [rng.next_float(0, 2.1, 2.11) for _ in range(1000)]
        assert min(samples) >= 2.1
        assert max(samples) < 2.11

    def test_zero_scale(self):
        rng = SFPURNG(seed=1)
        result = rng.next_float(0, 5.0, 5.0)
        assert result == 5.0
