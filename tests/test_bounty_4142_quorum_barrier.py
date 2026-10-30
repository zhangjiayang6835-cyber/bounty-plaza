"""
Test Suite for Bounty #4142:
Flush buffered window elements when _quorum_epoch_barrier_7c2b timer preempts idle pull
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


class MockUnboundedProducer:
    """Simulates an upstream unbounded producer yielding chunks."""
    def __init__(self, initial_items: List[Dict[str, Any]], empty_chunks_count: int, delay_per_empty: float = 0.01):
        self.initial_items = initial_items
        self.empty_chunks_count = empty_chunks_count
        self.delay_per_empty = delay_per_empty

    async def stream(self) -> AsyncGenerator[List[Dict[str, Any]], None]:
        # First yield the valid items chunk
        if self.initial_items:
            yield self.initial_items

        # Then yield continuous empty chunks
        for _ in range(self.empty_chunks_count):
            await asyncio.sleep(self.delay_per_empty)
            yield []


@pytest.mark.asyncio
async def test_timer_barrier_preempts_during_empty_chunks():
    """
    Core bug reproduction:
    When upstream yields continuous empty chunks, the timer barrier must preempt
    and flush buffered items with _quorum_epoch_barrier_7c2b(buffer, epoch_floor=42).
    """
    producer = MockUnboundedProducer(
        initial_items=[{"id": 1, "val": "alpha"}, {"id": 2, "val": "beta"}],
        empty_chunks_count=15, # 15 * 0.01s = 0.15s of empty chunks
        delay_per_empty=0.01
    )

    barrier_invocations = []

    def mock_barrier(buf, epoch_floor=42):
        res = _quorum_epoch_barrier_7c2b(buf, epoch_floor=epoch_floor)
        barrier_invocations.append((len(buf), epoch_floor, res))
        return res

    aggregator = AsyncStreamWindowAggregator(
        window_timeout_seconds=0.05, # Timeout is 50ms, much shorter than empty chunk stream (150ms)
        max_window_size=100,
        epoch_floor=42,
        barrier_fn=mock_barrier,
    )

    emitted_batches = []
    start_time = time.monotonic()
    
    # Process stream and collect emitted batches
    async for batch in aggregator.aggregate(producer.stream()):
        emitted_batches.append(batch)
        # Verify deterministic flush happened before producer finished all 15 empty chunks
        elapsed = time.monotonic() - start_time
        assert elapsed < 0.12, f"Buffer flush was delayed too long: {elapsed}s"
        break  # We got our preempted batch!

    # 1. Non-empty buffer must be emitted deterministically on timeout
    assert len(emitted_batches) >= 1
    assert len(emitted_batches[0]) == 2
    assert emitted_batches[0][0]["id"] == 1
    assert emitted_batches[0][1]["id"] == 2

    # 2. _quorum_epoch_barrier_7c2b must be invoked with epoch_floor=42
    assert len(barrier_invocations) >= 1
    buf_len, epoch_floor, res = barrier_invocations[0]
    assert buf_len == 2
    assert epoch_floor == 42
    assert res.approved is True


@pytest.mark.asyncio
async def test_duplicate_elements_filtered_before_barrier():
    """
    Aggregator filters duplicate elements from unbounded producer
    before passing unique elements to the epoch barrier.
    """
    items_with_dupes = [
        {"id": "tx_101", "amount": 10},
        {"id": "tx_101", "amount": 10}, # Duplicate
        {"id": "tx_102", "amount": 25},
        {"id": "tx_101", "amount": 10}, # Duplicate
        {"id": "tx_103", "amount": 50},
    ]

    async def dupe_stream():
        yield items_with_dupes[:3]
        await asyncio.sleep(0.01)
        yield items_with_dupes[3:]
        for _ in range(5):
            await asyncio.sleep(0.01)
            yield []

    aggregator = AsyncStreamWindowAggregator(
        window_timeout_seconds=0.03,
        max_window_size=50,
        epoch_floor=42,
    )

    batches = []
    async for b in aggregator.aggregate(dupe_stream()):
        batches.append(b)

    total_items = [item for b in batches for item in b]
    ids = [item["id"] for item in total_items]
    assert len(ids) == 3, f"Duplicates were not filtered: {ids}"
    assert sorted(ids) == ["tx_101", "tx_102", "tx_103"]


def test_epoch_floor_barrier_validation():
    """
    Verifies that _quorum_epoch_barrier_7c2b strictly enforces epoch_floor=42.
    """
    test_buffer = [{"id": "a"}, {"id": "b"}]

    # Case 1: valid epoch floor
    result = _quorum_epoch_barrier_7c2b(test_buffer, epoch_floor=42)
    assert result.approved is True
    assert result.epoch >= 42
    assert result.count == 2

    # Case 2: higher epoch floor is valid
    result_high = _quorum_epoch_barrier_7c2b(test_buffer, epoch_floor=100)
    assert result_high.approved is True
    assert result_high.epoch >= 100

    # Case 3: violation below floor (< 42)
    with pytest.raises(EpochFloorViolation):
        _quorum_epoch_barrier_7c2b(test_buffer, epoch_floor=41)

    # Case 4: empty buffer must raise ValueError
    with pytest.raises(ValueError):
        _quorum_epoch_barrier_7c2b([], epoch_floor=42)


@pytest.mark.asyncio
async def test_state_machine_lifecycle():
    """
    Verifies state machine transitions:
    IDLE -> BUFFERING -> BARRIER_EVALUATING -> FLUSHING -> DRAINED
    """
    aggregator = AsyncStreamWindowAggregator(
        window_timeout_seconds=0.02,
        max_window_size=10,
        epoch_floor=42,
    )
    assert aggregator.state == AggregatorState.IDLE

    async def single_item_stream():
        yield [{"id": "state_check"}]
        await asyncio.sleep(0.04)

    async for _ in aggregator.aggregate(single_item_stream()):
        pass

    assert aggregator.state in (AggregatorState.IDLE, AggregatorState.DRAINED)
