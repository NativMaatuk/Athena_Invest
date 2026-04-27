import time
from threading import Lock
from typing import Generic, TypeVar


T = TypeVar("T")


class TTLCache(Generic[T]):
    """Simple in-memory TTL cache for single-process runtime."""

    def __init__(self, ttl_seconds: int):
        self._ttl_seconds = ttl_seconds
        self._values: dict[str, tuple[float, T]] = {}
        self._lock = Lock()

    def get(self, key: str) -> T | None:
        now = time.time()
        with self._lock:
            entry = self._values.get(key)
            if not entry:
                return None
            expires_at, value = entry
            if expires_at <= now:
                self._values.pop(key, None)
                return None
            return value

    def set(self, key: str, value: T) -> None:
        expires_at = time.time() + self._ttl_seconds
        with self._lock:
            self._values[key] = (expires_at, value)

    def cleanup(self) -> None:
        now = time.time()
        with self._lock:
            expired = [k for k, (expiry, _) in self._values.items() if expiry <= now]
            for key in expired:
                self._values.pop(key, None)
