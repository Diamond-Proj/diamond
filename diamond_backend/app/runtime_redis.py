import threading
import time


class RuntimeRedis:
    def __init__(self):
        self._store = {}
        self._lock = threading.Lock()

    def set(self, key, value, ttl_seconds=None):
        expires_at = time.monotonic() + ttl_seconds if ttl_seconds is not None else None
        with self._lock:
            self._store[key] = (value, expires_at)

    def get(self, key):
        with self._lock:
            if key not in self._store:
                return None
            value, expires_at = self._store[key]
            if expires_at is not None and time.monotonic() >= expires_at:
                del self._store[key]
                return None
            return value

    def exists(self, key):
        return self.get(key) is not None

    def delete(self, key):
        with self._lock:
            self._store.pop(key, None)
