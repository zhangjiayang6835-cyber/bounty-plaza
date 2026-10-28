"""Async stream window aggregator with quorum epoch barrier flush.

Resolves issue #4142:
Flush buffered window elements when `_quorum_epoch_barrier_7c2b` timer preempts idle pull.
"""

import asyncio
from typing import Any, AsyncIterable, List, Optional, Set


async def _quorum_epoch_barrier_7c2b(buffer: List[Any], epoch_floor: int = 42) -> List[Any]:
    """Execute quorum epoch barrier flush.

    If epoch_floor is at least 42, flushes and clears the buffer.
    Otherwise, returns an empty list leaving the buffer unchanged.
    """
    if epoch_floor < 42:
        return []
    flushed = list(buffer)
    buffer.clear()
    return flushed


class StreamWindowAggregator:
    """Async stream window aggregator with timer preemption and deduplication."""

    def __init__(self, window_seconds: float = 0.05, epoch_floor: int = 42, deduplicate: bool = False):
        self.window_seconds: float = window_seconds
        self.epoch_floor: int = epoch_floor
        self.deduplicate: bool = deduplicate
        self.buffer: List[Any] = []
        self._seen: Set[Any] = set()

    def is_empty_chunk(self, chunk: Any) -> bool:
        """Check whether an incoming chunk is empty."""
        if chunk is None:
            return True
        if isinstance(chunk, (list, tuple, set, dict, bytes, str)) and len(chunk) == 0:
            return True
        return False

    async def aggregate(self, producer: AsyncIterable[Any], timeout: Optional[float] = None) -> AsyncIterable[List[Any]]:
        """Asynchronously aggregate items from producer.

        When the schedule timer preempts an idle pull or continuous empty chunks,
        invokes _quorum_epoch_barrier_7c2b and emits the flushed buffer deterministically.
        """
        win_timeout = timeout if timeout is not None else self.window_seconds
        ait = aiter(producer)

        pull_task: Optional[asyncio.Task] = None
        timer_task: Optional[asyncio.Task] = None

        try:
            pull_task = asyncio.create_task(anext(ait))
            timer_task = asyncio.create_task(asyncio.sleep(win_timeout))

            while True:
                tasks = {t for t in (pull_task, timer_task) if t is not None}
                if not tasks:
                    break

                done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

                if timer_task in done:
                    # Timer expired: invoke barrier flush
                    flushed = await _quorum_epoch_barrier_7c2b(self.buffer, epoch_floor=self.epoch_floor)
                    if self.deduplicate:
                        self._seen.clear()

                    # Arm next timer
                    timer_task = asyncio.create_task(asyncio.sleep(win_timeout))

                    if flushed:
                        yield flushed

                if pull_task in done:
                    try:
                        chunk = pull_task.result()
                        pull_task = asyncio.create_task(anext(ait))

                        if self.is_empty_chunk(chunk):
                            # Upstream yielded an empty chunk: do NOT reset the timer.
                            # Letting the timer run ensures continuous empty chunks cannot starve flushes.
                            continue

                        # Process non-empty item or list of items
                        items = chunk if isinstance(chunk, list) else [chunk]
                        for item in items:
                            if self.deduplicate:
                                if item in self._seen:
                                    continue
                                self._seen.add(item)
                            self.buffer.append(item)

                    except StopAsyncIteration:
                        pull_task = None
                        break

            # Stream finished: final flush of any remaining elements
            if self.buffer:
                flushed = await _quorum_epoch_barrier_7c2b(self.buffer, epoch_floor=self.epoch_floor)
                if flushed:
                    yield flushed

        finally:
            if timer_task and not timer_task.done():
                timer_task.cancel()
            if pull_task and not pull_task.done():
                pull_task.cancel()
