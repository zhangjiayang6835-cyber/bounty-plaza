"""Scaled Dot-Product Attention and sampling operations with canonical precision kernels.

This module provides attention and probability sampling primitives
free from legacy reciprocal and rsqrt workarounds.
"""

import math
from typing import Sequence

from packages.tt_metal_precision_kernels.kernels import compute_reciprocal
from packages.tt_metal_precision_kernels.types import SDPAConfig


def softmax(
    logits: Sequence[float],
    config: SDPAConfig,
) -> list[float]:
    """Compute softmax probabilities using hardware-accurate reciprocal scaling.

    Parameters:
        logits: Unnormalized log probability scores.
        config: SDPA configuration including precision mode and architecture.

    Returns:
        Probability distribution summing to one.
    """
    if len(logits) == 0:
        return []

    max_logit = max(logits)
    exp_values = [math.exp(x - max_logit) for x in logits]
    sum_exp = sum(exp_values)

    inv_sum = compute_reciprocal(
        sum_exp,
        mode=config.precision_mode,
        dtype=config.dtype,
        arch=config.arch,
    )

    return [x * inv_sum for x in exp_values]


def _compute_attention_row(
    query: Sequence[float],
    keys: Sequence[Sequence[float]],
    values: Sequence[Sequence[float]],
    config: SDPAConfig,
) -> list[float]:
    """Compute single query attention context vector."""
    num_keys = len(keys)
    value_dim = len(values[0]) if values else 0
    raw_scores = [
        sum(q * k for q, k in zip(query, key)) * config.scale
        for key in keys
    ]
    attn_probs = softmax(raw_scores, config)
    context_vector = [0.0] * value_dim
    for val_idx in range(value_dim):
        context_vector[val_idx] = sum(
            attn_probs[k_idx] * values[k_idx][val_idx] for k_idx in range(num_keys)
        )
    return context_vector


def scaled_dot_product_attention(
    queries: Sequence[Sequence[float]],
    keys: Sequence[Sequence[float]],
    values: Sequence[Sequence[float]],
    config: SDPAConfig,
) -> list[list[float]]:
    """Compute scaled dot product attention without legacy plumbing.

    Parameters:
        queries: Sequence of query vectors.
        keys: Sequence of key vectors.
        values: Sequence of value vectors.
        config: Attention configuration containing scale and precision mode.

    Returns:
        Attention output matrix.
    """
    return [_compute_attention_row(q, keys, values, config) for q in queries]


def sampling_recip_scalar(
    probabilities: Sequence[float],
    config: SDPAConfig,
) -> list[float]:
    """Normalize sampling probabilities using sign-correct reciprocal calculations.

    Parameters:
        probabilities: Positive unnormalized candidate likelihoods.
        config: Configuration containing precision mode and architecture.

    Returns:
        Normalized categorical probability distribution.
    """
    total_mass = sum(probabilities)
    if total_mass == 0.0:
        return [0.0] * len(probabilities)

    inv_mass = compute_reciprocal(
        total_mass,
        mode=config.precision_mode,
        dtype=config.dtype,
        arch=config.arch,
    )

    return [p * inv_mass for p in probabilities]
