"""
Security Fuzzing and Concurrency Stress Test Suite for Bounty #4142.
Validates CWE-400, CWE-362, adversarial inputs, and monotonic epoch guarantees.
"""

import asyncio
import pytest
import time
from typing import AsyncGenerator, List, Dict, Any

from solutions.quorum_epoch_barrier import (
    _quorum_epoch_barrier_7c2b,
    EpochFloorViolation,
    QuorumBarrierResult,
)
from solutions.stream_window_aggregator import (
    AsyncStreamWindowAggregator,
    AggregatorState,
)


@pytest.mark.asyncio
async def test_cwe_400_unbounded_producer_window_capping():
    """
    CWE-400: Validates that max_window_size strictly caps buffer growth
    preventing memory exhaustion under high-throughput producers.
    """
    async def high_volume_stream():
        for i in range(250):
            yield [{"id": f"item_{i}", "payload": "x" * 100}]

    aggregator = AsyncStreamWindowAggregator(
        window_timeout_seconds=1.0,
        max_window_size=25,
        epoch_floor=42,
    )

    batches = []
    async for batch in aggregator.aggregate(high_volume_stream()):
        batches.append(batch)
        assert len(batch) <= 25, f"Batch size {len(batch)} exceeded max_window_size 25"

    total_emitted = sum(len(b) for b in batches)
    assert total_emitted == 250
    assert len(batches) == 10  # 250 / 25 = 10 full batches


@pytest.mark.asyncio
async def test_cwe_362_concurrent_bursts_and_empty_stalls():
    """
    CWE-362: Simulates interleaved bursts of valid items and empty chunk stalls
    ensuring zero race condition deadlocks or buffer drops.
    """
    async def chaotic_stream():
        # Burst 1
        yield [{"id": "b1_1"}, {"id": "b1_2"}]
        # Stall with empty chunks
        for _ in range(5):
            await asyncio.sleep(0.01)
            yield []
        # Burst 2 with a duplicate
        yield [{"id": "b1_2"}, {"id": "b2_1"}, {"id": "b2_2"}]
        # Another stall
        for _ in range(5):
            await asyncio.sleep(0.01)
            yield []

    aggregator = AsyncStreamWindowAggregator(
        window_timeout_seconds=0.03,
        max_window_size=50,
        epoch_floor=42,
    )

    all_received = []
    async for batch in aggregator.aggregate(chaotic_stream()):
        for item in batch:
            all_received.append(item["id"])

    assert "b1_1" in all_received
    assert "b1_2" in all_received
    assert "b2_1" in all_received
    assert "b2_2" in all_received
    # Total count must be 4 distinct items
    assert len(all_received) == 4


@pytest.mark.asyncio
async def test_empty_producer_stream():
    """
    Validates that an empty producer drains cleanly without error or barrier invocation.
    """
    async def empty_stream():
        if False:
            yield []

    barrier_called = False

    def check_barrier(buf, floor):
        nonlocal barrier_called
        barrier_called = True
        return _quorum_epoch_barrier_7c2b(buf, floor)

    aggregator = AsyncStreamWindowAggregator(
        window_timeout_seconds=0.02,
        max_window_size=10,
        barrier_fn=check_barrier,
    )

    batches = []
    async for b in aggregator.aggregate(empty_stream()):
        batches.append(b)

    assert len(batches) == 0
    assert not barrier_called
    assert aggregator.state == AggregatorState.DRAINED


@pytest.mark.asyncio
async def test_monotonic_epoch_incrementation():
    """
    Validates that consecutive window flushes strictly advance the epoch monotonically.
    """
    async def multi_window_stream():
        for w in range(5):
            yield [{"id": f"win_{w}_item"}]
            await asyncio.sleep(0.04) # Allow timeout to trigger flush

    aggregator = AsyncStreamWindowAggregator(
        window_timeout_seconds=0.02,
        max_window_size=10,
        epoch_floor=42,
    )

    epochs_observed = []
    async for _ in aggregator.aggregate(multi_window_stream()):
        epochs_observed.append(aggregator.current_epoch)

    assert len(epochs_observed) == 5
    # Must be strictly increasing: [43, 44, 45, 46, 47]
    for i in range(len(epochs_observed) - 1):
        assert epochs_observed[i + 1] > epochs_observed[i]


def test_adversarial_barrier_inputs():
    """
    Fuzzes _quorum_epoch_barrier_7c2b with non-dict objects, unicode, and nested structures.
    """
    heterogeneous_buffer = [
        42,
        "string_element",
        {"nested": {"structure": [1, 2, 3]}},
        [10, 20, 30],
        True,
        None,
    ]

    res = _quorum_epoch_barrier_7c2b(heterogeneous_buffer, epoch_floor=50)
    assert res.approved is True
    assert res.epoch == 50
    assert res.count == 6
    assert res.checksum is not None
    assert len(res.checksum) == 16
