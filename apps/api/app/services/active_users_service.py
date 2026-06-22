from __future__ import annotations

import time
from threading import Lock


class ActiveUsersService:
    def __init__(self, window_seconds: int = 300):
        self._window_seconds = max(60, int(window_seconds))
        self._last_seen_by_session: dict[str, float] = {}
        self._lock = Lock()

    @property
    def window_seconds(self) -> int:
        return self._window_seconds

    def touch(self, session_id: str) -> int:
        now = time.time()
        with self._lock:
            self._last_seen_by_session[session_id] = now
            self._cleanup(now)
            return len(self._last_seen_by_session)

    def active_count(self) -> int:
        now = time.time()
        with self._lock:
            self._cleanup(now)
            return len(self._last_seen_by_session)

    def _cleanup(self, now_ts: float) -> None:
        threshold = now_ts - self._window_seconds
        stale_keys = [sid for sid, last_seen in self._last_seen_by_session.items() if last_seen < threshold]
        for sid in stale_keys:
            self._last_seen_by_session.pop(sid, None)
