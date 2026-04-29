from src.shared.metrics import MetricsCollector


def test_metrics_snapshot_handles_empty_and_single_values():
    metrics = MetricsCollector()
    snapshot = metrics.snapshot()
    assert snapshot["p95_latency_ms"] == 0.0
    assert snapshot["requests_total"] == 0

    metrics.record_success(120.0)
    snapshot = metrics.snapshot()
    assert snapshot["p95_latency_ms"] == 120.0
    assert snapshot["success_total"] == 1


def test_metrics_snapshot_calculates_p95_for_multiple_values():
    metrics = MetricsCollector()
    for latency in [100, 120, 140, 160, 180]:
        metrics.record_success(latency)

    snapshot = metrics.snapshot()
    assert snapshot["requests_total"] == 5
    assert snapshot["error_total"] == 0
    assert snapshot["p95_latency_ms"] >= 100.0
