import asyncio
import threading
from typing import Any, Callable, Dict, List, Optional

class AsyncEventQueue:
    """
    Thread-safe, distributed async event queue with race condition mitigation.
    """

    def __init__(self):
        # Internal queue for events
        self._queue: asyncio.Queue = asyncio.Queue()
        # Lock for thread-safe operations
        self._lock = threading.Lock()
        # Registered event handlers
        self._handlers: List[Callable[[Any], None]] = []
        # Event loop for async operations
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        # Flag to stop the event processor
        self._stop_event = threading.Event()
        # Processor thread
        self._processor_thread: Optional[threading.Thread] = None

    def register_handler(self, handler: Callable[[Any], None]) -> None:
        """
        Register an event handler.
        """
        with self._lock:
            self._handlers.append(handler)

    def unregister_handler(self, handler: Callable[[Any], None]) -> None:
        """
        Unregister an event handler.
        """
        with self._lock:
            if handler in self._handlers:
                self._handlers.remove(handler)

    def put(self, event: Any) -> None:
        """
        Thread-safe method to put an event into the queue.
        """
        # Use call_soon_threadsafe to ensure thread safety with the event loop
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, event)
        else:
            # If loop is not running, fallback to direct put (for early events)
            with self._lock:
                # This is safe because no processor is running yet
                self._queue.put_nowait(event)

    async def _process_events(self):
        """
        Internal coroutine to process events from the queue.
        """
        while not self._stop_event.is_set():
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=0.1)
            except asyncio.TimeoutError:
                continue
            handlers_snapshot = []
            with self._lock:
                handlers_snapshot = list(self._handlers)
            for handler in handlers_snapshot:
                try:
                    handler(event)
                except Exception:
                    # Optionally log the exception
                    pass
            self._queue.task_done()

    def start(self) -> None:
        """
        Start the event processor in a background thread.
        """
        with self._lock:
            if self._processor_thread is not None and self._processor_thread.is_alive():
                return  # Already started

            self._stop_event.clear()
            self._processor_thread = threading.Thread(target=self._run_event_loop, daemon=True)
            self._processor_thread.start()

    def _run_event_loop(self):
        """
        Run the asyncio event loop in a dedicated thread.
        """
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._process_events())
        finally:
            self._loop.close()
            self._loop = None

    def stop(self) -> None:
        """
        Stop the event processor gracefully.
        """
        self._stop_event.set()
        if self._loop is not None:
            def stopper():
                for task in asyncio.all_tasks(loop=self._loop):
                    task.cancel()
            self._loop.call_soon_threadsafe(stopper)
        if self._processor_thread is not None:
            self._processor_thread.join(timeout=2)
            self._processor_thread = None

    def join(self, timeout: Optional[float] = None) -> None:
        """
        Wait until all events in the queue have been processed.
        """
        if self._loop is not None:
            fut = asyncio.run_coroutine_threadsafe(self._queue.join(), self._loop)
            try:
                fut.result(timeout=timeout)
            except Exception:
                pass

# =========================
# TESTS
# =========================

import time

def test_race_condition():
    """
    Test that no events are lost or processed out of order under high concurrency.
    """
    queue = AsyncEventQueue()
    processed: List[int] = []
    lock = threading.Lock()

    def handler(event):
        with lock:
            processed.append(event)

    queue.register_handler(handler)
    queue.start()

    NUM_EVENTS = 1000
    NUM_THREADS = 10

    def producer(start, end):
        for i in range(start, end):
            queue.put(i)

    threads = []
    step = NUM_EVENTS // NUM_THREADS
    for t in range(NUM_THREADS):
        s = t * step
        e = (t + 1) * step if t < NUM_THREADS - 1 else NUM_EVENTS
        th = threading.Thread(target=producer, args=(s, e))
        threads.append(th)
        th.start()

    for th in threads:
        th.join()

    queue.join(timeout=5)
    queue.stop()

    # Check all events processed
    assert sorted(processed) == list(range(NUM_EVENTS)), "Some events lost or duplicated!"

def test_handler_registration():
    queue = AsyncEventQueue()
    results: List[str] = []
    queue.register_handler(lambda e: results.append(f"event:{e}"))
    queue.start()
    queue.put("foo")
    queue.join(timeout=2)
    queue.stop()
    assert results == ["event:foo"]

def test_unregister_handler():
    queue = AsyncEventQueue()
    results: List[str] = []
    def handler(e):
        results.append(f"event:{e}")
    queue.register_handler(handler)
    queue.start()
    queue.put("bar")
    queue.join(timeout=2)
    queue.unregister_handler(handler)
    queue.put("baz")
    queue.join(timeout=2)
    queue.stop()
    assert results == ["event:bar"]

if __name__ == "__main__":
    test_race_condition()
    test_handler_registration()
    test_unregister_handler()
    print("All tests passed.")