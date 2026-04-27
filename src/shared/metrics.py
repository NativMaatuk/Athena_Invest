from collections import deque
from statistics import quantiles
from threading import Lock


class MetricsCollector:
    """Tracks core runtime metrics in-memory."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._requests_total = 0
        self._success_total = 0
        self._error_total = 0
        self._latencies_ms = deque(maxlen=1000)

    def record_success(self, latency_ms: float) -> None:
        with self._lock:
            self._requests_total += 1
            self._success_total += 1
            self._latencies_ms.append(latency_ms)

    def record_error(self, latency_ms: float | None = None) -> None:
        with self._lock:
            self._requests_total += 1
            self._error_total += 1
            if latency_ms is not None:
                self._latencies_ms.append(latency_ms)

    def snapshot(self) -> dict:
        with self._lock:
            latencies = list(self._latencies_ms)
            p95 = 0.0
            if len(latencies) >= 2:
                p95 = quantiles(latencies, n=100)[94]
            elif len(latencies) == 1:
                p95 = latencies[0]

            return {
                "requests_total": self._requests_total,
                "success_total": self._success_total,
                "error_total": self._error_total,
                "p95_latency_ms": round(p95, 2),
            }
