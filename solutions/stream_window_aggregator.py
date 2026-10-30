"""
Async Stream Window Aggregator with Preemptive Quorum Epoch Barrier.
Flushes buffered window elements deterministically when schedule timer preempts idle pull.
"""

# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-branches
# pylint: disable=too-many-statements,too-few-public-methods,broad-exception-caught
# pylint: disable=line-too-long,too-many-instance-attributes,import-error

import asyncio
from collections import OrderedDict
from enum import Enum
import json
import time
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    List,
    Optional,
    Tuple,
)

from solutions.quorum_epoch_barrier import (
    _quorum_epoch_barrier_7c2b,
    QuorumBarrierResult,
)


class AggregatorState(str, Enum):
    """Lifecycle states of the stream window aggregator."""
    IDLE = "IDLE"
    BUFFERING = "BUFFERING"
    BARRIER_EVALUATING = "BARRIER_EVALUATING"
    FLUSHING = "FLUSHING"
    DRAINED = "DRAINED"


class AsyncStreamWindowAggregator:
    """
    Aggregates asynchronous stream items into deduplicated time/size bounded windows.
    Guarantees deterministic barrier flush when the schedule timer preempts an idle pull
    or when upstream yields continuous empty chunks.
    """

    def __init__(
        self,
        window_timeout_seconds: float = 0.05,
        max_window_size: int = 100,
        epoch_floor: int = 42,
        barrier_fn: Optional[Callable[[List[Any], int], QuorumBarrierResult]] = None,
        dedup_key: Optional[str] = "id",
        dedup_cache_size: int = 10000,
    ):
        self.window_timeout_seconds = window_timeout_seconds
        self.max_window_size = max_window_size
        self.epoch_floor = max(42, epoch_floor)
        self.barrier_fn = barrier_fn or _quorum_epoch_barrier_7c2b
        self.dedup_key = dedup_key
        self.dedup_cache_size = dedup_cache_size

        self.state = AggregatorState.IDLE
        self.current_epoch = self.epoch_floor
        self._buffer: List[Any] = []
        self._seen_signatures: OrderedDict[str, None] = OrderedDict()

    def _extract_item_signature(self, item: Any) -> str:
        """Extracts a unique deduplication signature for an item."""
        if isinstance(item, dict):
            if self.dedup_key and self.dedup_key in item:
                return f"key:{item[self.dedup_key]}"
            try:
                return json.dumps(item, sort_keys=True)
            except (TypeError, ValueError):
                return str(item)
        return str(item)

    def _register_signature(self, sig: str) -> bool:
        """Registers a signature in the bounded deduplication cache. Returns True if newly seen."""
        if sig in self._seen_signatures:
            return False
        if len(self._seen_signatures) >= self.dedup_cache_size:
            self._seen_signatures.popitem(last=False)
        self._seen_signatures[sig] = None
        return True

    def _flush_buffer(self) -> List[Any]:
        """Invokes the quorum epoch barrier and flushes current window buffer."""
        if not self._buffer:
            return []

        self.state = AggregatorState.BARRIER_EVALUATING
        # Enforce quorum barrier contract
        barrier_result = self.barrier_fn(self._buffer, self.epoch_floor)

        if not barrier_result.approved:
            msg = "Quorum barrier rejected window buffer"
            raise RuntimeError(msg)

        self.state = AggregatorState.FLUSHING
        emitted_batch = list(self._buffer)

        # Clear buffer and advance epoch
        self._buffer.clear()
        self.current_epoch += 1

        self.state = AggregatorState.BUFFERING
        return emitted_batch

    async def aggregate(
        self,
        stream: AsyncGenerator[List[Any], None],
    ) -> AsyncGenerator[List[Any], None]:
        """
        Consumes chunks from an async stream generator, aggregating elements
        and flushing windows deterministically upon timeout or size threshold.
        """
        self.state = AggregatorState.BUFFERING
        queue: asyncio.Queue[Tuple[bool, Any]] = asyncio.Queue(maxsize=1000)

        async def _feeder_task():
            try:
                async for chunk in stream:
                    await queue.put((False, chunk))
            except Exception as exc:
                await queue.put((True, exc))
                return
            await queue.put((True, None))

        feeder = asyncio.create_task(_feeder_task())
        window_start: Optional[float] = None

        try:
            while True:
                # Compute remaining time if buffer has pending items
                if self._buffer:
                    if window_start is None:
                        window_start = time.monotonic()
                    elapsed = time.monotonic() - window_start
                    remaining = max(0.001, self.window_timeout_seconds - elapsed)
                else:
                    window_start = None
                    remaining = None

                try:
                    if remaining is not None:
                        is_terminal, payload = await asyncio.wait_for(
                            queue.get(), timeout=remaining
                        )
                    else:
                        is_terminal, payload = await queue.get()

                except asyncio.TimeoutError:
                    # Timeout barrier triggered! Flush buffer deterministically
                    if self._buffer:
                        flushed = self._flush_buffer()
                        window_start = None
                        yield flushed
                    continue

                if is_terminal:
                    if isinstance(payload, Exception):
                        raise payload
                    # Upstream producer finished
                    break

                chunk = payload
                if chunk:
                    for item in chunk:
                        sig = self._extract_item_signature(item)
                        if self._register_signature(sig):
                            self._buffer.append(item)

                    if window_start is None and self._buffer:
                        window_start = time.monotonic()

                    # Immediate flush on reaching maximum window size
                    if len(self._buffer) >= self.max_window_size:
                        flushed = self._flush_buffer()
                        window_start = None
                        yield flushed

                else:
                    # Upstream yielded an empty chunk
                    # Preemption check: if timer has expired while receiving empty chunks, flush now
                    if self._buffer and window_start is not None:
                        if time.monotonic() - window_start >= self.window_timeout_seconds:
                            flushed = self._flush_buffer()
                            window_start = None
                            yield flushed

            # Final drain flush on EOF
            if self._buffer:
                flushed = self._flush_buffer()
                yield flushed

        finally:
            if not feeder.done():
                feeder.cancel()
                try:
                    await feeder
                except asyncio.CancelledError:
                    pass
            self.state = AggregatorState.DRAINED
