"""Async stream window aggregator with quorum epoch barrier flush (#4142).

Resolves Issue #4142:
Flush buffered window elements when `_quorum_epoch_barrier_7c2b` timer preempts idle pull.
"""

import asyncio
from typing import Any, AsyncIterable, List, Optional, Set


async def _quorum_epoch_barrier_7c2b(
    buffer: List[Any], epoch_floor: int = 42
) -> List[Any]:
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

    def __init__(
        self,
        window_seconds: float = 0.05,
        epoch_floor: int = 42,
        deduplicate: bool = False,
    ):
        """Initialize aggregator parameters."""
        self.window_seconds: float = window_seconds
        self.epoch_floor: int = epoch_floor
        self.deduplicate: bool = deduplicate
        self.buffer: List[Any] = []
        self._seen: Set[Any] = set()

    @staticmethod
    def is_empty_chunk(chunk: Any) -> bool:
        """Check whether an incoming chunk is empty."""
        if chunk is None:
            return True
        if isinstance(chunk, (list, tuple, set, dict, bytes, str)):
            return len(chunk) == 0
        return False

    def _append_chunk_items(self, chunk: Any) -> None:
        """Add non-empty chunk items to the buffer with optional deduplication."""
        items = chunk if isinstance(chunk, list) else [chunk]
        for item in items:
            if self.deduplicate and item in self._seen:
                continue
            if self.deduplicate:
                self._seen.add(item)
            self.buffer.append(item)

    async def _flush_barrier(self) -> List[Any]:
        """Trigger quorum epoch barrier flush on current buffer."""
        flushed = await _quorum_epoch_barrier_7c2b(
            self.buffer, epoch_floor=self.epoch_floor
        )
        if self.deduplicate:
            self._seen.clear()
        return flushed

    async def aggregate(
        self, producer: AsyncIterable[Any], timeout: Optional[float] = None
    ) -> AsyncIterable[List[Any]]:
        """Asynchronously aggregate items from producer.

        When the schedule timer preempts an idle pull or continuous empty chunks,
        invokes _quorum_epoch_barrier_7c2b and emits the flushed buffer deterministically.
        """
        win_timeout = timeout if timeout is not None else self.window_seconds
        ait = aiter(producer)

        pull_task: Optional[asyncio.Task] = asyncio.create_task(anext(ait))
        timer_task: Optional[asyncio.Task] = asyncio.create_task(
            asyncio.sleep(win_timeout)
        )

        try:
            while pull_task is not None:
                tasks = {t for t in (pull_task, timer_task) if t is not None}
                done, _ = await asyncio.wait(
                    tasks, return_when=asyncio.FIRST_COMPLETED
                )

                if timer_task in done:
                    flushed = await self._flush_barrier()
                    timer_task = asyncio.create_task(asyncio.sleep(win_timeout))
                    if flushed:
                        yield flushed

                if pull_task in done:
                    pull_task, should_exit = self._process_pull_done(pull_task, ait)
                    if should_exit:
                        break

            final_flush = await self._flush_barrier()
            if final_flush:
                yield final_flush

        finally:
            for task in (timer_task, pull_task):
                if task and not task.done():
                    task.cancel()

    def _process_pull_done(
        self, done_task: asyncio.Task, ait: Any
    ) -> tuple[Optional[asyncio.Task], bool]:
        """Handle completed pull task and arm next pull."""
        try:
            chunk = done_task.result()
            next_task = asyncio.create_task(anext(ait))
            if not self.is_empty_chunk(chunk):
                self._append_chunk_items(chunk)
            return next_task, False
        except StopAsyncIteration:
            return None, True
