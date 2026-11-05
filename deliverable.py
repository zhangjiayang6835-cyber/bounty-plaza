"""Fix for issue #4142: timer barrier must flush a non-empty window even while
upstream keeps yielding empty chunks.

`_quorum_epoch_barrier_7c2b(buffer, epoch_floor=42)` consumes an async source,
deduplicates by value, and emits each unique element once. A per-pull timer
bounds how long a buffered element may wait: if the timer wins the race against
the next pull, the entire non-empty buffer is emitted immediately, so an
unbounded producer of empty chunks cannot starve the barrier. Items below
`epoch_floor` are dropped before they can enter the buffer, and cancellation
leaves no outstanding pull task behind.
"""
from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Awaitable, Callable, Iterable, List, Optional

DEFAULT_FLUSH_SECONDS = 0.05


async def _next_or_none(pull: Callable[[], Awaitable[Any]]) -> Any:
    try:
        return await pull()
    except StopAsyncIteration:
        return _DONE


class _Done:
    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return "<done>"


_DONE = _Done()


def _epoch_of(item: Any) -> Optional[int]:
    if isinstance(item, dict):
        for key in ("epoch", "epoch_id", "seq_epoch"):
            if key in item:
                value = item[key]
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return None
    return None


async def _collect(buffer: Iterable[Any]) -> AsyncIterator[Any]:
    for item in buffer:
        yield item


async def _quorum_epoch_barrier_7c2b(
    buffer: Any,
    epoch_floor: int = 42,
    flush_seconds: float = DEFAULT_FLUSH_SECONDS,
) -> AsyncIterator[Any]:
    iterator = buffer.__aiter__() if hasattr(buffer, "__aiter__") else _collect(buffer).__aiter__()

    seen = set()
    pending: List[Any] = []
    finished = False

    async def pull() -> Any:
        return await iterator.__anext__()

    while not finished:
        task = asyncio.ensure_future(_next_or_none(pull))
        try:
            done, _pending = await asyncio.wait({task}, timeout=flush_seconds)
            if not done:
                # Timer won the race: emit everything buffered, deterministically.
                if pending:
                    batch, pending = pending, []
                    for item in batch:
                        yield item
                else:
                    # Nothing buffered: still await the pull so items are not lost.
                    item = await task
                    if item is _DONE:
                        finished = True
                    else:
                        _absorb(item, seen, pending, epoch_floor)
                continue
            item = task.result()
        except asyncio.CancelledError:
            task.cancel()
            raise
        finally:
            if not task.done():
                task.cancel()

        if item is _DONE:
            finished = True
        else:
            _absorb(item, seen, pending, epoch_floor)

    if pending:
        for item in pending:
            yield item


def _absorb(item: Any, seen: set, pending: List[Any], epoch_floor: int) -> None:
    epoch = _epoch_of(item)
    if epoch is not None and epoch < epoch_floor:
        return
    key = _key(item)
    if key in seen:
        return
    seen.add(key)
    pending.append(item)


def _key(item: Any) -> Any:
    if isinstance(item, dict):
        for key in ("id", "key", "hash", "seq"):
            if key in item:
                return ("k", item[key])
        return ("d", tuple(sorted((str(k), str(v)) for k, v in item.items())))
    try:
        hash(item)
        return ("v", item)
    except TypeError:
        return ("r", repr(item))
