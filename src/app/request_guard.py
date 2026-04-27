import time


class RequestGuard:
    """Applies per-user cooldown policy."""

    def __init__(self, cooldown_seconds: int):
        self._cooldown_seconds = cooldown_seconds
        self._last_seen: dict[int, float] = {}

    def can_process(self, user_id: int) -> tuple[bool, int]:
        now = time.time()
        last = self._last_seen.get(user_id)
        if last is not None:
            elapsed = now - last
            if elapsed < self._cooldown_seconds:
                remaining = int(self._cooldown_seconds - elapsed)
                return False, max(1, remaining)
        self._last_seen[user_id] = now
        return True, 0
