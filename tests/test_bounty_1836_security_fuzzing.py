"""
Adversarial Security & Robustness Fuzzing Suite for Issue #1836 (ttnn.sampling)
Maps to CWE / OWASP attack vectors for tensor operations and hardware device kernels.
"""

import math
import pytest
import numpy as np

from solutions.ttnn_sampling_resolution_fix import (
    DeviceSamplingPipeline,
    Philox4x32,
    SamplingConfig,
    TensixArchitecture,
    ttnn_sampling,
)


class TestTTNNSamplingSecurityFuzzing:
    """Adversarial security tests for ttnn.sampling"""

    def test_cwe_682_nan_logits_rejection(self):
        """CWE-682: Input logits containing NaN must be rejected immediately."""
        logits = np.array([1.0, float("nan"), 3.0], dtype=np.float32)
        pipe = DeviceSamplingPipeline(SamplingConfig())
        with pytest.raises(ValueError, match="NaN"):
            pipe.sample_token(logits)

    def test_cwe_682_all_neginf_logits_rejection(self):
        """CWE-682: All negative infinity logits (all tokens masked) must be rejected."""
        logits = np.array([-np.inf, -np.inf, -np.inf], dtype=np.float32)
        pipe = DeviceSamplingPipeline(SamplingConfig())
        with pytest.raises(ValueError, match="-infinity"):
            pipe.sample_token(logits)

    def test_cwe_125_empty_vocabulary_rejection(self):
        """CWE-125: Zero-length logits vector must raise ValueError without out-of-bounds access."""
        logits = np.array([], dtype=np.float32)
        pipe = DeviceSamplingPipeline(SamplingConfig())
        with pytest.raises(ValueError, match="cannot be 0"):
            pipe.sample_token(logits)

    def test_single_token_vocabulary_safe(self):
        """Edge case: Vocabulary size = 1 must trivially and safely return index 0."""
        logits = np.array([42.0], dtype=np.float32)
        pipe = DeviceSamplingPipeline(SamplingConfig(seed=123))
        for _ in range(10):
            tok = pipe.sample_token(logits)
            assert tok == 0

    def test_cwe_125_large_vocabulary_llama3_scale(self):
        """
        CWE-125 / Buffer bounds:
        Verify stability with Llama-3 vocabulary size (V = 128,256 tokens).
        """
        vocab_size = 128256
        # Sparsely populated logits
        logits = np.full(vocab_size, -100.0, dtype=np.float32)
        logits[100] = 5.0
        logits[50000] = 6.0
        logits[120000] = 5.5

        sampled = ttnn_sampling(logits, seed=333, top_k=50)
        assert 0 <= sampled < vocab_size
        assert sampled in {100, 50000, 120000}

    def test_cwe_682_extreme_dynamic_range(self):
        """
        CWE-682: Numerical stability with extreme logits [-10000.0, +10000.0].
        Softmax must not overflow to Inf or NaN.
        """
        logits = np.array([-10000.0, 10000.0, -5000.0, 0.0], dtype=np.float32)
        pipe = DeviceSamplingPipeline(SamplingConfig(seed=456))
        # The token with logit 10000.0 has probability ~1.0
        tok = pipe.sample_token(logits)
        assert tok == 1

    def test_cwe_190_counter_overflow_fuzzing(self):
        """
        CWE-190: PRNG counter wrapping around 2^32 - 1 boundary without crash.
        """
        max_u32 = 0xFFFFFFFF
        prng = Philox4x32((12345, 67890))
        # Call with counter near 2^32 - 1
        words1 = prng.generate([max_u32 - 1, 0, 0, 0])
        words2 = prng.generate([max_u32, 0, 0, 0])
        words3 = prng.generate([0, 1, 0, 0])  # wrapped

        assert len(words1) == 4
        assert len(words2) == 4
        assert len(words3) == 4
        assert words1 != words2 != words3

    def test_cwe_330_prng_bit_independence(self):
        """
        CWE-330: Verify Philox-4x32 outputs are well-distributed across all bit positions.
        """
        prng = Philox4x32((0xABCD1234, 0x5678EF01))
        num_trials = 1000
        bit_counts = np.zeros(32, dtype=np.int32)

        for i in range(num_trials):
            words = prng.generate([i, 0, 0, 0])
            w = words[0]
            for bit in range(32):
                if (w >> bit) & 1:
                    bit_counts[bit] += 1

        # Each bit should be 1 approximately 50% of the time (40% to 60% range)
        for bit in range(32):
            ratio = bit_counts[bit] / num_trials
            assert 0.40 <= ratio <= 0.60, f"Bit {bit} biased: ratio={ratio:.3f}"

    def test_subnormal_temperature_stabilization(self):
        """
        Robustness: Tiny subnormal temperature (e.g. 1e-12) must safely degenerate to greedy argmax.
        """
        logits = np.array([2.0, 5.0, 3.0], dtype=np.float32)
        pipe = DeviceSamplingPipeline(SamplingConfig(temperature=1e-12))
        tok = pipe.sample_token(logits)
        assert tok == 1
