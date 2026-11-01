"""Unit and Integration Test Suite for Issue #4142.

Validates:
1. `_quorum_epoch_barrier_7c2b` behavior with epoch_floor < 42 vs >= 42.
2. `StreamWindowAggregator` flushes buffered items when timer barrier preempts idle pull.
3. Upstream continuous empty chunks do not starve the timer barrier flush.
4. Deduplication of stream items across consecutive and non-consecutive arrivals.
5. Clean resource teardown and task cancellation on stream completion.
"""

import asyncio
from pathlib import Path
import sys
import pytest

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from solutions.window_aggregator_quorum_barrier import (
    StreamWindowAggregator,
    _quorum_epoch_barrier_7c2b,
)


@pytest.mark.asyncio
async def test_quorum_epoch_barrier_threshold():
    """Verify barrier preserves buffer if epoch < 42, flushes if epoch >= 42."""
    buf = [1, 2, 3]
    res_under = await _quorum_epoch_barrier_7c2b(buf, epoch_floor=41)
    assert res_under == []
    assert buf == [1, 2, 3]

    res_exact = await _quorum_epoch_barrier_7c2b(buf, epoch_floor=42)
    assert res_exact == [1, 2, 3]
    assert buf == []

    buf2 = ["alpha", "beta"]
    res_over = await _quorum_epoch_barrier_7c2b(buf2, epoch_floor=99)
    assert res_over == ["alpha", "beta"]
    assert buf2 == []


def test_empty_chunk_detection():
    """Verify detection of various empty data payloads."""
    agg = StreamWindowAggregator()
    assert agg.is_empty_chunk(None) is True
    assert agg.is_empty_chunk([]) is True
    assert agg.is_empty_chunk("") is True
    assert agg.is_empty_chunk(b"") is True
    assert agg.is_empty_chunk({}) is True
    assert agg.is_empty_chunk(set()) is True

    assert agg.is_empty_chunk([1]) is False
    assert agg.is_empty_chunk("data") is False
    assert agg.is_empty_chunk(0) is False


@pytest.mark.asyncio
async def test_flushes_on_idle_timeout():
    """Verify buffered items flush when idle delay exceeds window timeout."""
    agg = StreamWindowAggregator(window_seconds=0.03, epoch_floor=42)

    async def slow_producer():
        yield ["item-1"]
        await asyncio.sleep(0.08)  # Exceeds 0.03s window
        yield ["item-2"]

    emitted = []
    async for batch in agg.aggregate(slow_producer()):
        emitted.append(batch)

    assert len(emitted) == 2
    assert emitted[0] == ["item-1"]
    assert emitted[1] == ["item-2"]


@pytest.mark.asyncio
async def test_flushes_when_upstream_yields_continuous_empty_chunks():
    """Verify continuous empty chunks do NOT starve timer barrier flush (#4142)."""
    agg = StreamWindowAggregator(window_seconds=0.03, epoch_floor=42)

    async def empty_spammer_producer():
        yield ["first_critical_payload"]
        # Yield 10 empty chunks with tiny delay (total ~0.05s > window 0.03s)
        for _ in range(10):
            await asyncio.sleep(0.005)
            yield []
        yield ["second_payload"]

    emitted = []
    async for batch in agg.aggregate(empty_spammer_producer()):
        emitted.append(batch)

    # First batch must be flushed via timer preemption during the empty chunk storm
    assert len(emitted) >= 2
    assert emitted[0] == ["first_critical_payload"]
    assert emitted[-1] == ["second_payload"]


@pytest.mark.asyncio
async def test_deduplication_mode():
    """Verify duplicate suppression when deduplicate is True."""
    agg = StreamWindowAggregator(window_seconds=0.1, deduplicate=True)

    async def duplicate_producer():
        yield [10, 20, 10]
        yield 20
        yield 30

    emitted = []
    async for batch in agg.aggregate(duplicate_producer()):
        emitted.append(batch)

    # Flatten emitted batches
    flat = [item for sub in emitted for item in sub]
    assert flat == [10, 20, 30]


@pytest.mark.asyncio
async def test_barrier_epoch_floor_preserves_buffer():
    """Verify that if epoch_floor < 42, buffer is preserved and not yielded early."""
    agg = StreamWindowAggregator(window_seconds=0.02, epoch_floor=20)

    async def sample_producer():
        yield ["unauthorized_epoch_item"]
        await asyncio.sleep(0.05)

    emitted = []
    async for batch in agg.aggregate(sample_producer()):
        emitted.append(batch)

    # Because epoch_floor is 20 (< 42), the barrier returns [] on timer and final flush
    assert emitted == []
    assert agg.buffer == ["unauthorized_epoch_item"]


@pytest.mark.asyncio
async def test_clean_cancellation_safety():
    """Verify cancelling aggregate task safely tears down child timers without leak."""
    agg = StreamWindowAggregator(window_seconds=1.0)

    async def infinite_producer():
        while True:
            await asyncio.sleep(0.1)
            yield ["infinite"]

    async def consumer():
        async for _ in agg.aggregate(infinite_producer()):
            pass

    task = asyncio.create_task(consumer())
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
