"""Tests for issue #4142: the barrier must flush on timeout and never emit twice."""
import asyncio
import unittest

from deliverable import _quorum_epoch_barrier_7c2b


class Source:
    """Async source with scripted delays, so the timer race is controllable."""

    def __init__(self, items):
        self.items = list(items)
        self.delays = []
        self.pulls = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.items:
            raise StopAsyncIteration
        self.pulls += 1
        delay = self.items.pop(0)
        if isinstance(delay, tuple) and delay and delay[0] == "sleep":
            await asyncio.sleep(delay[1])
            return delay[2]
        return delay


async def drain(source, **kwargs):
    out = []
    async for item in _quorum_epoch_barrier_7c2b(source, **kwargs):
        out.append(item)
    return out


class TestBarrier(unittest.TestCase):
    def test_flushes_buffer_while_upstream_yields_empty_chunks(self):
        # one real element, then a long run of empty chunks: timer must win
        src = Source([{"id": 1}, "", "", "", "", "", ""])
        out = asyncio.run(drain(src, flush_seconds=0.01))
        self.assertIn({"id": 1}, out)
        self.assertEqual(out.count({"id": 1}), 1)
        self.assertEqual([x for x in out if x != ""], [{"id": 1}])

    def test_deduplicates_repeated_elements(self):
        src = Source([{"id": 1}, {"id": 1}, {"id": 2}, "x", "x"])
        out = asyncio.run(drain(src, flush_seconds=0.01))
        self.assertEqual(out.count({"id": 1}), 1)
        self.assertEqual(out.count({"id": 2}), 1)
        self.assertEqual(out.count("x"), 1)

    def test_epoch_floor_filters_old_items(self):
        src = Source([{"id": 1, "epoch": 41}, {"id": 2, "epoch": 42}, {"id": 3, "epoch": 7}])
        out = asyncio.run(drain(src, epoch_floor=42, flush_seconds=0.01))
        self.assertEqual([i["id"] for i in out], [2])

    def test_fast_source_keeps_order(self):
        src = Source([{"id": n} for n in range(5)])
        out = asyncio.run(drain(src, flush_seconds=0.05))
        self.assertEqual([i["id"] for i in out], [0, 1, 2, 3, 4])

    def test_no_outstanding_pull_after_completion(self):
        async def main():
            src = Source([{"id": 1}, {"id": 2}])
            out = await drain(src, flush_seconds=0.01)
            leftovers = [t for t in asyncio.all_tasks() if not t.done() and t is not asyncio.current_task()]
            return out, leftovers, src.pulls

        out, leftovers, pulls = asyncio.run(main())
        self.assertEqual([i["id"] for i in out], [1, 2])
        self.assertEqual(leftovers, [])
        self.assertEqual(pulls, 2)

    def test_cancellation_propagates(self):
        async def main():
            src = Source([("sleep", 5, {"id": 1})])
            task = asyncio.ensure_future(drain(src, flush_seconds=0.01))
            await asyncio.sleep(0.02)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        asyncio.run(main())


if __name__ == "__main__":
    unittest.main(verbosity=2)
