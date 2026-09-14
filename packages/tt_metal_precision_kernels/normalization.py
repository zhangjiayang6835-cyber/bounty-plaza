"""Normalization layers operating via non-legacy precision kernels.

This module provides implementations of LayerNorm, RMSNorm, GroupNorm,
and distributed normalization routines using canonical rsqrt and reciprocal paths.
All legacy compatibility configurations and bypass flags have been eliminated.
"""

from typing import Sequence

from packages.tt_metal_precision_kernels.kernels import compute_rsqrt
from packages.tt_metal_precision_kernels.types import (
    Architecture,
    GroupNormConfig,
    LayerNormConfig,
    RMSNormConfig,
)


def _compute_mean_variance(
    inputs: Sequence[float],
    use_welford: bool,
) -> tuple[float, float]:
    """Calculate mean and variance with optional Welford algorithm."""
    length = len(inputs)
    if length == 0:
        return 0.0, 0.0

    if use_welford:
        count = 0
        online_mean = 0.0
        m2 = 0.0
        for val in inputs:
            count += 1
            delta = val - online_mean
            online_mean += delta / count
            delta2 = val - online_mean
            m2 += delta * delta2
        return online_mean, m2 / count

    mean = sum(inputs) / length
    variance = sum((x - mean) ** 2 for x in inputs) / length
    return mean, variance


def layer_norm(
    inputs: Sequence[float],
    gamma: Sequence[float],
    beta: Sequence[float],
    config: LayerNormConfig,
    arch: Architecture = Architecture.WORMHOLE_B0,
) -> list[float]:
    """Execute LayerNorm over an input sequence without compatibility plumbing.

    Parameters:
        inputs: Input activations sequence.
        gamma: Scale parameter weights.
        beta: Bias parameter weights.
        config: LayerNorm configuration object without deprecated fields.
        arch: Target Tenstorrent hardware architecture.

    Returns:
        Normalized output activation values.
    """
    length = len(inputs)
    if length == 0:
        return []

    mean, variance = _compute_mean_variance(inputs, config.use_welford)

    inv_std = compute_rsqrt(
        variance + config.eps,
        mode=config.precision_mode,
        dtype=config.dtype,
        arch=arch,
    )

    output: list[float] = []
    for idx in range(length):
        normalized = (inputs[idx] - mean) * inv_std
        output.append(normalized * gamma[idx] + beta[idx])
    return output


def rms_norm(
    inputs: Sequence[float],
    weight: Sequence[float],
    config: RMSNormConfig,
    arch: Architecture = Architecture.WORMHOLE_B0,
) -> list[float]:
    """Execute RMSNorm over an input sequence using high-precision rsqrt.

    Parameters:
        inputs: Input activations sequence.
        weight: Scale parameter weights.
        config: RMSNorm configuration object.
        arch: Target Tenstorrent hardware architecture.

    Returns:
        Normalized output activation values.
    """
    length = len(inputs)
    if length == 0:
        return []

    mean_squared = sum(x * x for x in inputs) / length

    inv_rms = compute_rsqrt(
        mean_squared + config.eps,
        mode=config.precision_mode,
        dtype=config.dtype,
        arch=arch,
    )

    output: list[float] = []
    for idx in range(length):
        output.append(inputs[idx] * inv_rms * weight[idx])
    return output


def _normalize_group(
    group_slice: Sequence[float],
    start_idx: int,
    weights: tuple[Sequence[float], Sequence[float]],
    config: GroupNormConfig,
    arch: Architecture,
) -> list[float]:
    """Normalize a single channel group slice."""
    gamma, beta = weights
    mean, variance = _compute_mean_variance(group_slice, False)

    inv_std = compute_rsqrt(
        variance + config.eps,
        mode=config.precision_mode,
        dtype=config.dtype,
        arch=arch,
    )

    group_output: list[float] = []
    for elem_idx, val in enumerate(group_slice):
        global_idx = start_idx + elem_idx
        norm_val = (val - mean) * inv_std
        group_output.append(norm_val * gamma[global_idx] + beta[global_idx])
    return group_output


def group_norm(
    inputs: Sequence[float],
    gamma: Sequence[float],
    beta: Sequence[float],
    config: GroupNormConfig,
    arch: Architecture = Architecture.WORMHOLE_B0,
) -> list[float]:
    """Execute GroupNorm partitioning inputs into groups and normalizing.

    Parameters:
        inputs: Flat sequence representing channel activations.
        gamma: Channel scale parameters.
        beta: Channel bias parameters.
        config: GroupNorm configuration specifying group count and precision.
        arch: Target Tenstorrent hardware architecture.

    Returns:
        Group normalized output sequence.
    """
    total_len = len(inputs)
    num_groups = config.num_groups
    group_size = total_len // num_groups

    result: list[float] = []
    for group_idx in range(num_groups):
        start = group_idx * group_size
        end = start + group_size
        slice_result = _normalize_group(
            inputs[start:end], start, (gamma, beta), config, arch
        )
        result.extend(slice_result)
    return result


def distributed_rms_norm(
    shards: Sequence[Sequence[float]],
    weights: Sequence[float],
    config: RMSNormConfig,
    arch: Architecture = Architecture.WORMHOLE_B0,
) -> list[list[float]]:
    """Simulate distributed RMSNorm across tensor-parallel device shards.

    Parameters:
        shards: List of activation vectors across participating devices.
        weights: Sharded weights corresponding to device features.
        config: RMSNorm configuration parameters.
        arch: Target hardware architecture.

    Returns:
        List of normalized shards from each device.
    """
    num_shards = len(shards)
    if num_shards == 0:
        return []

    shard_length = len(shards[0])
    total_elements = num_shards * shard_length

    sum_squares = sum(sum(x * x for x in shard) for shard in shards)
    global_mean_squared = sum_squares / total_elements

    global_inv_rms = compute_rsqrt(
        global_mean_squared + config.eps,
        mode=config.precision_mode,
        dtype=config.dtype,
        arch=arch,
    )

    outputs: list[list[float]] = []
    for shard in shards:
        normalized_shard: list[float] = []
        for idx, val in enumerate(shard):
            normalized_shard.append(val * global_inv_rms * weights[idx])
        outputs.append(normalized_shard)
    return outputs
