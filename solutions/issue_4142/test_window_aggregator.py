"""Unit tests for issue #4142: StreamWindowAggregator and _quorum_epoch_barrier_7c2b."""

import asyncio
import unittest
import pytest

from solutions.issue_4142.window_aggregator import (
    StreamWindowAggregator,
    _quorum_epoch_barrier_7c2b,
)


class TestQuorumEpochBarrier(unittest.IsolatedAsyncioTestCase):
    """Test suite for quorum epoch barrier function."""

    async def test_quorum_barrier_flushes_when_epoch_floor_met(self):
        buffer = ["val_a", "val_b", "val_c"]
        flushed = await _quorum_epoch_barrier_7c2b(buffer, epoch_floor=42)
        self.assertEqual(flushed, ["val_a", "val_b", "val_c"])
        self.assertEqual(buffer, [], "Buffer must be emptied after barrier flush")

    async def test_quorum_barrier_rejects_sub_floor_epoch(self):
        buffer = ["x1", "x2"]
        flushed = await _quorum_epoch_barrier_7c2b(buffer, epoch_floor=41)
        self.assertEqual(flushed, [])
        self.assertEqual(buffer, ["x1", "x2"], "Buffer must remain intact on rejected floor")

    async def test_quorum_barrier_empty_buffer(self):
        buffer = []
        flushed = await _quorum_epoch_barrier_7c2b(buffer, epoch_floor=50)
        self.assertEqual(flushed, [])


class TestStreamWindowStateMachine(unittest.IsolatedAsyncioTestCase):
    """Test suite for stream window aggregator state machine."""

    async def test_idle_pull_timer_preempts_and_flushes(self):
        """Timer wins race over slow producer and flushes buffered elements."""
        window = StreamWindowAggregator(window_seconds=0.03, epoch_floor=42)

        async def slow_producer():
            yield "item1"
            yield "item2"
            # Producer idles longer than window_seconds
            await asyncio.sleep(0.08)
            yield "item3"

        emitted = []
        async for batch in window.aggregate(slow_producer()):
            emitted.append(batch)

        self.assertGreaterEqual(len(emitted), 2)
        self.assertEqual(emitted[0], ["item1", "item2"])
        self.assertIn("item3", emitted[-1])

    async def test_continuous_empty_chunks_do_not_starve_timer_flush(self):
        """Continuous empty chunks do not reset timer; timer fires deterministically."""
        window = StreamWindowAggregator(window_seconds=0.04, epoch_floor=42)

        async def empty_chunks_producer():
            yield ["elem1", "elem2"]
            # Upstream sends continuous empty chunks
            for _ in range(5):
                await asyncio.sleep(0.01)
                yield []
                yield None
            await asyncio.sleep(0.05)
            yield "elem3"

        emitted = []
        async for batch in window.aggregate(empty_chunks_producer()):
            emitted.append(batch)

        self.assertGreaterEqual(len(emitted), 2)
        self.assertEqual(emitted[0], ["elem1", "elem2"])
        self.assertEqual(emitted[-1], ["elem3"])

    async def test_deduplication_in_window(self):
        """Duplicate items within the window are filtered."""
        window = StreamWindowAggregator(window_seconds=0.05, epoch_floor=42, deduplicate=True)

        async def dup_producer():
            yield ["k1", "k2", "k1", "k2", "k3"]

        batches = [b async for b in window.aggregate(dup_producer())]
        self.assertEqual(batches, [["k1", "k2", "k3"]])


if __name__ == "__main__":
    unittest.main()
