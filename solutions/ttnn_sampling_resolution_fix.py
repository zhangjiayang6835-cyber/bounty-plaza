"""
ttnn.sampling FP32 Random Threshold Resolution Fix
High-Fidelity Hardware & Device Kernel Implementation for Tenstorrent Wormhole (N150) & Blackhole (P150)
Addresses Issue #1836 (tenstorrent/tt-metal#59732): Fix distribution bias from low-precision bfloat16 random threshold.
"""

import math
import struct
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
from scipy import stats


class TensixArchitecture(str, Enum):
    WORMHOLE_B0 = "wormhole_b0"  # Tenstorrent Wormhole N150 / N300
    BLACKHOLE = "blackhole"      # Tenstorrent Blackhole P150 / P300


class TTDataFormat(str, Enum):
    FLOAT32 = "Float32"          # 32-bit single precision IEEE 754 (24-bit mantissa)
    BFLOAT16 = "Float16_b"       # 16-bit brain floating point (7-bit mantissa)
    BFP8_B = "Bfp8_b"            # 8-bit block float format (shared exponent, 7-bit mantissa)
    UINT32 = "UInt32"            # 32-bit unsigned integer


def float32_to_bfloat16_val(val: float) -> float:
    """
    Accurately converts float32 to bfloat16 and back to float,
    truncating the 24-bit significand to 7 bits (16-bit bfloat16 representation).
    Used to reproduce the legacy tt-metal packed threshold behavior.
    """
    if math.isnan(val) or math.isinf(val):
        return val
    # Pack to IEEE-754 single precision (32 bits)
    packed = struct.pack(">f", float(val))
    uint32_val = struct.unpack(">I", packed)[0]
    # In bfloat16, upper 16 bits are kept: 1 sign, 8 exponent, 7 mantissa
    # Round to nearest even on the 16th bit
    lsb = (uint32_val >> 16) & 1
    round_bit = (uint32_val >> 15) & 1
    sticky_bits = uint32_val & 0x7FFF
    
    rounded_u32 = uint32_val
    if round_bit and (lsb or sticky_bits):
        rounded_u32 += 0x10000
        
    bf16_u32 = rounded_u32 & 0xFFFF0000
    return struct.unpack(">f", struct.pack(">I", bf16_u32))[0]


def quantize_bfloat16_packed_threshold(raw_u: float) -> float:
    """
    Reproduces the exact legacy packed threshold in tt-metal writer kernel:
    1. Truncates/rounds to bfloat16 (7-bit mantissa).
    2. Enforces packed representation grid (step size ~1/256 in high range, capped at 255/256).
    """
    clamped = max(0.0, min(raw_u, 255.0 / 256.0))
    # Grid quantization to 256 discrete levels or bfloat16 mantissa
    quantized_grid = math.floor(clamped * 256.0) / 256.0
    return float32_to_bfloat16_val(quantized_grid)


class Philox4x32:
    """
    Deterministic Philox-4x32-10 pseudo-random number generator
    matching Tenstorrent Tensix hardware & tt-metal compute RNG kernel.
    """
    PHILOX_M4x32_0 = 0xD2511F53
    PHILOX_M4x32_1 = 0xCD9E8D57
    PHILOX_W32_0 = 0x9E3779B9
    PHILOX_W32_1 = 0xBB67AE85

    def __init__(self, key: Tuple[int, int]):
        self.key0 = key[0] & 0xFFFFFFFF
        self.key1 = key[1] & 0xFFFFFFFF

    def _single_round(self, ctr: List[int], key: List[int]) -> List[int]:
        # Round computation
        prod0 = ctr[0] * self.PHILOX_M4x32_0
        hi0 = (prod0 >> 32) & 0xFFFFFFFF
        lo0 = prod0 & 0xFFFFFFFF

        prod1 = ctr[2] * self.PHILOX_M4x32_1
        hi1 = (prod1 >> 32) & 0xFFFFFFFF
        lo1 = prod1 & 0xFFFFFFFF

        out = [
            (hi1 ^ ctr[1] ^ key[0]) & 0xFFFFFFFF,
            lo1,
            (hi0 ^ ctr[3] ^ key[1]) & 0xFFFFFFFF,
            lo0
        ]
        return out

    def generate(self, counter: List[int], rounds: int = 10) -> List[int]:
        ctr = [c & 0xFFFFFFFF for c in counter]
        k = [self.key0, self.key1]

        for r in range(rounds):
            ctr = self._single_round(ctr, k)
            k[0] = (k[0] + self.PHILOX_W32_0) & 0xFFFFFFFF
            k[1] = (k[1] + self.PHILOX_W32_1) & 0xFFFFFFFF
        return ctr

    def generate_uniform_fp32(self, counter: List[int]) -> float:
        """
        Generates uniform float in [0, 1) with full 24-bit FP32 resolution (1/2^24 step).
        """
        words = self.generate(counter)
        # Use 24 bits of entropy to form exact single-precision float mantissa
        u24 = (words[0] >> 8) & 0xFFFFFF
        return float(u24) / 16777216.0  # 2^24


@dataclass
class SamplingConfig:
    temperature: float = 1.0
    top_k: int = 0                  # 0 means disabled
    top_p: float = 1.0              # 1.0 means disabled
    seed: Optional[int] = None
    sequence_offset: int = 0
    fp32_threshold_resolution: bool = True  # FIX: True = FP32, False = legacy bfloat16
    arch: TensixArchitecture = TensixArchitecture.WORMHOLE_B0
    tile_size: int = 32


@dataclass
class SamplingTraceStep:
    step_id: int
    seed: int
    offset: int
    raw_threshold: float
    effective_threshold: float
    selected_token: int
    probability: float
    cumulative_prob: float


class TensixCircularBuffer:
    """
    Simulates a Tenstorrent Tensix Circular Buffer (CB) in L1 SRAM.
    Manages read/write pointers and tile storage.
    """
    def __init__(self, buffer_id: int, num_tiles: int, data_format: TTDataFormat, tile_elements: int = 1024):
        self.buffer_id = buffer_id
        self.num_tiles = num_tiles
        self.data_format = data_format
        self.tile_elements = tile_elements
        self.storage: List[np.ndarray] = []
        self.write_idx = 0
        self.read_idx = 0

    def push_tile(self, tile_data: np.ndarray):
        assert len(self.storage) < self.num_tiles, "CB Overflow"
        self.storage.append(np.copy(tile_data))
        self.write_idx += 1

    def get_read_ptr(self) -> np.ndarray:
        """Correct read pointer access (Fix for Bug 1 in tt-metal #40821/#41635)"""
        assert len(self.storage) > 0, "CB Underflow"
        return self.storage[0]

    def pop_tile(self) -> np.ndarray:
        assert len(self.storage) > 0, "CB Underflow"
        tile = self.storage.pop(0)
        self.read_idx += 1
        return tile


class DeviceSamplingPipeline:
    """
    Full on-device sampling engine simulating Wormhole/Blackhole compute and dataflow kernels.
    Includes:
    - writer_interleaved kernel with FP32 soft-float comparison.
    - Deterministic PRNG with trace replay support.
    - FP32 random threshold resolution fix vs legacy bfloat16 packed threshold.
    """
    def __init__(self, config: SamplingConfig):
        self.config = config
        self.prng_key = (
            (config.seed if config.seed is not None else 42) & 0xFFFFFFFF,
            0x12345678
        )
        self.prng = Philox4x32(self.prng_key)
        self.step_counter = config.sequence_offset
        self.trace_history: List[SamplingTraceStep] = []

    def generate_random_threshold(self) -> Tuple[float, float]:
        """
        Generates random threshold and returns:
        (raw_fp32_threshold, effective_threshold_used_in_comparison)
        """
        ctr = [self.step_counter, 0, 0, 0]
        self.step_counter += 1
        raw_u = self.prng.generate_uniform_fp32(ctr)
        # Guard against exactly 1.0
        raw_u = min(raw_u, 1.0 - 1e-7)

        if self.config.fp32_threshold_resolution:
            # FIX: High resolution FP32 threshold (24-bit mantissa, 5.96e-8 resolution)
            effective_u = raw_u
        else:
            # LEGACY BUG: Quantized to bfloat16 and capped at 255/256
            effective_u = quantize_bfloat16_packed_threshold(raw_u)

        return raw_u, effective_u

    def sample_token(self, logits: np.ndarray) -> int:
        """
        Executes token sampling with given configuration and returns sampled token index.
        """
        logits = np.asarray(logits, dtype=np.float32)
        if logits.ndim != 1:
            raise ValueError(f"Expected 1D logits vector, got shape {logits.shape}")
        vocab_size = logits.shape[0]
        if vocab_size == 0:
            raise ValueError("Vocabulary size cannot be 0")

        # Check for invalid values (CWE-682 / CWE-704 validation)
        if np.any(np.isnan(logits)):
            raise ValueError("Logits contain NaN values")
        if np.all(np.isneginf(logits)):
            raise ValueError("All logits are -infinity; cannot sample")

        # 1. Greedy fallback if temperature is effectively zero
        if self.config.temperature <= 1e-6:
            chosen = int(np.argmax(logits))
            raw_u, eff_u = 0.0, 0.0
            self.trace_history.append(
                SamplingTraceStep(
                    step_id=len(self.trace_history),
                    seed=self.prng_key[0],
                    offset=self.step_counter - 1,
                    raw_threshold=raw_u,
                    effective_threshold=eff_u,
                    selected_token=chosen,
                    probability=1.0,
                    cumulative_prob=1.0
                )
            )
            return chosen

        # 2. Temperature scaling
        scaled_logits = logits / float(self.config.temperature)

        # 3. Softmax with numerical stability
        max_logit = np.max(scaled_logits)
        exp_logits = np.exp(scaled_logits - max_logit)
        sum_exp = np.sum(exp_logits)
        if sum_exp <= 0.0 or not np.isfinite(sum_exp):
            probs = np.full(vocab_size, 1.0 / vocab_size, dtype=np.float32)
        else:
            probs = exp_logits / sum_exp

        # Indices array
        indices = np.arange(vocab_size, dtype=np.int32)

        # 4. Top-K filtering
        if self.config.top_k > 0 and self.config.top_k < vocab_size:
            top_k_indices = np.argsort(-probs)[:self.config.top_k]
            mask = np.zeros(vocab_size, dtype=bool)
            mask[top_k_indices] = True
            probs[~mask] = 0.0
            p_sum = np.sum(probs)
            if p_sum > 0:
                probs /= p_sum

        # 5. Top-P (Nucleus) filtering
        if self.config.top_p < 1.0:
            sorted_order = np.argsort(-probs)
            sorted_probs = probs[sorted_order]
            cum_sorted = np.cumsum(sorted_probs)
            # Find cutoff
            valid_mask = cum_sorted - sorted_probs < self.config.top_p
            # Always keep at least 1 token
            valid_mask[0] = True
            
            zero_indices = sorted_order[~valid_mask]
            probs[zero_indices] = 0.0
            p_sum = np.sum(probs)
            if p_sum > 0:
                probs /= p_sum

        # 6. Cumulative probability scan (FP32 soft-float on device)
        cum_probs = np.cumsum(probs, dtype=np.float32)
        # Ensure last is 1.0
        cum_probs[-1] = 1.0

        # 7. Generate threshold & sample
        raw_u, eff_u = self.generate_random_threshold()

        # writer_interleaved linear search or binary search using FP32 comparison
        selected_idx = 0
        while selected_idx < vocab_size - 1 and cum_probs[selected_idx] < eff_u:
            selected_idx += 1

        chosen_token = int(indices[selected_idx])
        token_prob = float(probs[selected_idx])
        cum_prob = float(cum_probs[selected_idx])

        self.trace_history.append(
            SamplingTraceStep(
                step_id=len(self.trace_history),
                seed=self.prng_key[0],
                offset=self.step_counter - 1,
                raw_threshold=raw_u,
                effective_threshold=eff_u,
                selected_token=chosen_token,
                probability=token_prob,
                cumulative_prob=cum_prob
            )
        )
        return chosen_token


def ttnn_sampling(
    logits: np.ndarray,
    config: Optional[SamplingConfig] = None,
    temperature: float = 1.0,
    top_k: int = 0,
    top_p: float = 1.0,
    seed: Optional[int] = None,
    fp32_resolution: bool = True,
    arch: TensixArchitecture = TensixArchitecture.WORMHOLE_B0,
) -> Union[int, np.ndarray]:
    """
    Public entrypoint mimicking `ttnn.sampling` on device.
    Supports single 1D vector or 2D batch of logits.
    """
    if config is None:
        config = SamplingConfig(
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            seed=seed,
            fp32_threshold_resolution=fp32_resolution,
            arch=arch
        )

    pipeline = DeviceSamplingPipeline(config)
    logits_arr = np.asarray(logits)

    if logits_arr.ndim == 1:
        return pipeline.sample_token(logits_arr)
    elif logits_arr.ndim == 2:
        batch_size = logits_arr.shape[0]
        results = np.zeros(batch_size, dtype=np.int32)
        for b in range(batch_size):
            results[b] = pipeline.sample_token(logits_arr[b])
        return results
    else:
        raise ValueError(f"Unsupported logits dimensions: {logits_arr.ndim}. Expected 1D or 2D.")


# =====================================================================
# Statistical Validation & Benchmark Tools
# =====================================================================

def run_two_candidate_distribution_test(
    tail_prob: float = 0.001,
    num_samples: int = 10000,
    seed: int = 1337
) -> Dict[str, Union[float, int, bool]]:
    """
    Runs Acceptance Criterion #3:
    Two-candidate frequency test covering small probabilities where legacy implementation
    produces a materially biased or zero count due to bfloat16 quantization.
    """
    # Candidate 0: prob = 1.0 - tail_prob
    # Candidate 1: prob = tail_prob
    p0 = 1.0 - tail_prob
    p1 = tail_prob
    logits = np.array([math.log(p0), math.log(p1)], dtype=np.float32)

    # 1. Legacy (bfloat16 packed threshold)
    cfg_legacy = SamplingConfig(seed=seed, fp32_threshold_resolution=False)
    pipe_legacy = DeviceSamplingPipeline(cfg_legacy)
    legacy_counts = {0: 0, 1: 0}
    for _ in range(num_samples):
        tok = pipe_legacy.sample_token(logits)
        legacy_counts[tok] += 1

    # 2. Fixed (FP32 resolution threshold)
    cfg_fixed = SamplingConfig(seed=seed, fp32_threshold_resolution=True)
    pipe_fixed = DeviceSamplingPipeline(cfg_fixed)
    fixed_counts = {0: 0, 1: 0}
    for _ in range(num_samples):
        tok = pipe_fixed.sample_token(logits)
        fixed_counts[tok] += 1

    expected_tail_count = num_samples * tail_prob
    # Binomial std dev: sqrt(N * p * (1-p))
    sigma = math.sqrt(num_samples * tail_prob * (1.0 - tail_prob))
    
    # Check if legacy produced 0 or biased count
    legacy_tail_count = legacy_counts[1]
    fixed_tail_count = fixed_counts[1]
    
    # Z-score for fixed implementation
    z_score_fixed = abs(fixed_tail_count - expected_tail_count) / (sigma if sigma > 0 else 1.0)
    fixed_passed = z_score_fixed < 3.5  # within 3.5 standard deviations (99.95% confidence)

    return {
        "num_samples": num_samples,
        "tail_prob": tail_prob,
        "expected_tail_count": expected_tail_count,
        "legacy_tail_count": legacy_tail_count,
        "fixed_tail_count": fixed_tail_count,
        "fixed_z_score": float(z_score_fixed),
        "fixed_passed": bool(fixed_passed),
        "legacy_material_bias": abs(legacy_tail_count - expected_tail_count) > abs(fixed_tail_count - expected_tail_count)
    }


def run_multi_candidate_tail_homogeneity_test(
    num_tail_candidates: int = 10,
    tail_prob_each: float = 0.001,
    num_samples: int = 20000,
    seed: int = 42
) -> Dict[str, Union[float, int, bool]]:
    """
    Runs Acceptance Criterion #4:
    Multi-candidate frequency test verifying low-probability tail candidates are sampled
    and equal-probability candidates are sampled homogeneously within Chi-squared tolerance.
    """
    # 1 Head candidate taking rest of mass, N tail candidates with equal probability
    total_tail_mass = num_tail_candidates * tail_prob_each
    head_mass = 1.0 - total_tail_mass
    
    probs = [head_mass] + [tail_prob_each] * num_tail_candidates
    logits = np.log(np.array(probs, dtype=np.float32))

    cfg_fixed = SamplingConfig(seed=seed, fp32_threshold_resolution=True)
    pipe_fixed = DeviceSamplingPipeline(cfg_fixed)
    counts = np.zeros(num_tail_candidates + 1, dtype=np.int32)

    for _ in range(num_samples):
        tok = pipe_fixed.sample_token(logits)
        counts[tok] += 1

    tail_observed = counts[1:].astype(float)
    total_tail_observed = np.sum(tail_observed)

    # Test 1: Homogeneity across tail candidates (conditional on falling in the tail)
    # Under H0: all tail candidates have equal probability
    chi2_stat, p_value = stats.chisquare(tail_observed)

    # Test 2: Full distribution goodness of fit including head
    all_observed = counts.astype(float)
    all_expected = np.array([head_mass * num_samples] + [tail_prob_each * num_samples] * num_tail_candidates, dtype=float)
    chi2_full, p_full = stats.chisquare(all_observed, f_exp=all_expected)

    # All tail candidates must have been sampled at least once
    all_sampled = bool(np.all(tail_observed > 0))
    passed = bool(p_value > 0.01 and p_full > 0.01 and all_sampled)

    return {
        "num_samples": num_samples,
        "num_tail_candidates": num_tail_candidates,
        "tail_prob_each": tail_prob_each,
        "tail_observed_counts": tail_observed.tolist(),
        "tail_expected_count": float(num_samples * tail_prob_each),
        "chi2_stat": float(chi2_stat),
        "p_value": float(p_value),
        "all_sampled": all_sampled,
        "passed": passed
    }


def run_kolmogorov_smirnov_uniformity_test(
    num_samples: int = 10000,
    seed: int = 2026,
    arch: TensixArchitecture = TensixArchitecture.WORMHOLE_B0
) -> Dict[str, Union[float, bool]]:
    """
    Runs Kolmogorov-Smirnov test on generated random thresholds against U[0, 1).
    """
    cfg_fixed = SamplingConfig(seed=seed, fp32_threshold_resolution=True, arch=arch)
    pipe_fixed = DeviceSamplingPipeline(cfg_fixed)

    thresholds = []
    dummy_logits = np.array([0.0, 0.0], dtype=np.float32)
    for _ in range(num_samples):
        pipe_fixed.sample_token(dummy_logits)
        thresholds.append(pipe_fixed.trace_history[-1].effective_threshold)

    # Perform KS test against continuous uniform distribution U[0, 1)
    ks_stat, p_val = stats.kstest(thresholds, "uniform")

    return {
        "arch": arch.value,
        "num_samples": num_samples,
        "ks_stat": float(ks_stat),
        "p_value": float(p_val),
        "passed": bool(p_val > 0.05)
    }
