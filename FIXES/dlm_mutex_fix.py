import threading
import time

class DistributedLockManager:
    """Atomic Mutex Lock Manager preventing TOCTOU Race Conditions (Issue #266)."""
    def __init__(self):
        self._locks = {}
        self._global_mutex = threading.Lock()

    def acquire_lock(self, resource_id: str, timeout_sec: float = 5.0) -> bool:
        start_time = time.time()
        with self._global_mutex:
            if resource_id not in self._locks:
                self._locks[resource_id] = threading.Lock()
        
        lock = self._locks[resource_id]
        return lock.acquire(timeout=timeout_sec)

    def release_lock(self, resource_id: str):
        with self._global_mutex:
            if resource_id in self._locks and self._locks[resource_id].locked():
                self._locks[resource_id].release()
