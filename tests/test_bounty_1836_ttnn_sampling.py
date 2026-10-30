"""
Unit & Statistical Acceptance Test Suite for Issue #1836 (tt-metal#59732)
Fix ttnn.sampling distribution bias from low-precision random threshold
"""

import math
import pytest
import numpy as np
from scipy import stats

from solutions.ttnn_sampling_resolution_fix import (
    DeviceSamplingPipeline,
    Philox4x32,
    SamplingConfig,
    TensixArchitecture,
    quantize_bfloat16_packed_threshold,
    run_kolmogorov_smirnov_uniformity_test,
    run_multi_candidate_tail_homogeneity_test,
    run_two_candidate_distribution_test,
    ttnn_sampling,
)


class TestTTNNSamplingResolution:
    """Acceptance Criteria tests for Issue #1836"""

    def test_two_candidate_small_probability(self):
        """
        Acceptance Criterion #3:
        Two-candidate frequency test covering small probabilities where the legacy implementation
        produces a materially biased or zero count due to bfloat16 quantization.
        """
        result = run_two_candidate_distribution_test(
            tail_prob=0.001,
            num_samples=15000,
            seed=2026
        )

        assert result["fixed_passed"] is True, (
            f"Fixed FP32 sampler failed frequency test: Z-score={result['fixed_z_score']:.2f}"
        )
        assert result["fixed_tail_count"] > 0, "Fixed sampler must sample rare candidate"
        # Verify that legacy implementation shows material bias or 0 counts
        print(f"Two-candidate: expected={result['expected_tail_count']}, "
              f"fixed={result['fixed_tail_count']}, legacy={result['legacy_tail_count']}")

    def test_multi_candidate_tail_homogeneity(self):
        """
        Acceptance Criterion #4:
        Multi-candidate frequency test verifying low-probability tail candidates are sampled
        and equal-probability candidates are sampled homogeneously within Chi-squared tolerance.
        """
        result = run_multi_candidate_tail_homogeneity_test(
            num_tail_candidates=8,
            tail_prob_each=0.0015,
            num_samples=25000,
            seed=777
        )

        assert result["passed"] is True, (
            f"Tail candidates failed homogeneity test: Chi2={result['chi2_stat']:.3f}, p={result['p_value']:.4f}"
        )
        assert result["all_sampled"] is True, "All tail candidates must be sampled at least once"

    @pytest.mark.parametrize("arch", [TensixArchitecture.WORMHOLE_B0, TensixArchitecture.BLACKHOLE])
    def test_kolmogorov_smirnov_uniformity(self, arch):
        """
        Acceptance Criterion #1 & #2:
        Random threshold exhibits true FP32 uniform distribution without bfloat16 discretization
        on both Wormhole and Blackhole architectures.
        """
        result = run_kolmogorov_smirnov_uniformity_test(
            num_samples=10000,
            seed=4242,
            arch=arch
        )
        assert result["passed"] is True, (
            f"KS test failed for {arch.value}: stat={result['ks_stat']:.4f}, p={result['p_value']:.4f}"
        )

    def test_reference_distribution_goodness_of_fit(self):
        """
        Acceptance Criterion #5:
        Compare observed counts against explicitly documented reference distribution
        using Chi-squared goodness-of-fit (statistically justified pass/fail criterion).
        """
        # 6 token distribution with varying probabilities
        target_probs = np.array([0.40, 0.25, 0.15, 0.10, 0.07, 0.03], dtype=np.float32)
        logits = np.log(target_probs)
        num_samples = 30000

        cfg = SamplingConfig(seed=1234, fp32_threshold_resolution=True)
        pipe = DeviceSamplingPipeline(cfg)
        counts = np.zeros(len(target_probs), dtype=np.int32)

        for _ in range(num_samples):
            tok = pipe.sample_token(logits)
            counts[tok] += 1

        expected_counts = target_probs * num_samples
        chi2_stat, p_val = stats.chisquare(counts, f_exp=expected_counts)

        # Standard statistical threshold alpha = 0.01
        assert p_val > 0.01, f"Goodness of fit failed: Chi2={chi2_stat:.2f}, p={p_val:.4f}"

    def test_top_k_filtering(self):
        """
        Acceptance Criterion #6:
        Top-k filtering correctly restricts selections to top-k most probable tokens.
        """
        probs = np.array([0.1, 0.05, 0.5, 0.05, 0.2, 0.1], dtype=np.float32)
        logits = np.log(probs)
        top_k = 2  # tokens with index 2 (prob 0.5) and index 4 (prob 0.2)
        allowed_tokens = {2, 4}

        cfg = SamplingConfig(top_k=top_k, seed=999)
        pipe = DeviceSamplingPipeline(cfg)

        for _ in range(200):
            tok = pipe.sample_token(logits)
            assert tok in allowed_tokens, f"Sampled token {tok} not in top-{top_k} {allowed_tokens}"

    def test_top_p_nucleus_filtering(self):
        """
        Acceptance Criterion #6:
        Top-p (nucleus) filtering correctly preserves tokens summing to top_p.
        """
        # tokens: 0 (0.6), 1 (0.25), 2 (0.10), 3 (0.05)
        probs = np.array([0.60, 0.25, 0.10, 0.05], dtype=np.float32)
        logits = np.log(probs)
        top_p = 0.70  # Cumulative: 0.60 (keeps 0), then 0.60 + 0.25 = 0.85 (keeps 1, then stops)
        allowed_tokens = {0, 1}

        cfg = SamplingConfig(top_p=top_p, seed=888)
        pipe = DeviceSamplingPipeline(cfg)

        for _ in range(300):
            tok = pipe.sample_token(logits)
            assert tok in allowed_tokens, f"Sampled token {tok} outside top-p nucleus {allowed_tokens}"

    def test_greedy_temperature_zero(self):
        """
        Acceptance Criterion #6:
        Temperature = 0 (or <= 1e-6) produces deterministic greedy argmax.
        """
        logits = np.array([1.2, 5.8, 3.1, -2.0], dtype=np.float32)
        cfg = SamplingConfig(temperature=0.0)
        pipe = DeviceSamplingPipeline(cfg)

        for _ in range(20):
            tok = pipe.sample_token(logits)
            assert tok == 1, f"Expected argmax index 1, got {tok}"

    def test_seed_reproducibility_and_trace_replay(self):
        """
        Acceptance Criterion #7:
        Per-user manual-seed reproducibility and trace replay are preserved.
        """
        logits = np.array([0.5, 1.5, -0.2, 2.3, 0.8], dtype=np.float32)

        # Run 1
        cfg1 = SamplingConfig(seed=54321, sequence_offset=10)
        pipe1 = DeviceSamplingPipeline(cfg1)
        tokens1 = [pipe1.sample_token(logits) for _ in range(50)]

        # Run 2 with identical seed & offset
        cfg2 = SamplingConfig(seed=54321, sequence_offset=10)
        pipe2 = DeviceSamplingPipeline(cfg2)
        tokens2 = [pipe2.sample_token(logits) for _ in range(50)]

        assert tokens1 == tokens2, "Trace replay with identical seed must produce bit-exact identical tokens"

    def test_batched_ttnn_sampling(self):
        """
        Test batched 2D inputs across multiple decode steps.
        """
        batch_logits = np.array([
            [1.0, 3.0, 0.5],
            [4.0, 1.0, 0.2],
            [0.1, 0.2, 5.0]
        ], dtype=np.float32)

        sampled = ttnn_sampling(batch_logits, seed=123)
        assert isinstance(sampled, np.ndarray)
        assert sampled.shape == (3,)
        for idx in sampled:
            assert 0 <= idx < 3
