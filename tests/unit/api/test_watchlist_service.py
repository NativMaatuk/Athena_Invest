from __future__ import annotations

from apps.api.app.services.watchlist_service import WatchlistService
from apps.api.app.storage.watchlist_store import WatchlistStore


def build_service(tmp_path) -> WatchlistService:
    store = WatchlistStore(str(tmp_path / "watchlist.db"))
    return WatchlistService(
        store=store,
        max_items=5,
        significant_change_pct=5,
        degraded_failure_threshold=3,
        retention_days=90,
    )


def test_build_events_detects_holder_reduction(tmp_path):
    service = build_service(tmp_path)
    previous = {
        "fetch_status": "ok",
        "institutional_pct": 70.0,
        "top_holders": [{"name": "BlackRock", "pct_out": 10.0}],
    }
    current = {
        "fetch_status": "ok",
        "institutional_pct": 64.0,
        "relative_volume": 2.4,
        "top_holders": [{"name": "BlackRock", "pct_out": 4.8}],
    }

    events = service._build_events(ticker="NVDA", previous=previous, current=current)

    event_types = {event["event_type"] for event in events}
    assert "institutional_pct_shift" in event_types
    assert "holder_reduced" in event_types
    reduced = next(event for event in events if event["event_type"] == "holder_reduced")
    assert reduced["severity"] in {"medium", "high"}


def test_parse_since_normalizes_to_utc():
    iso = WatchlistService.parse_since("2026-06-21T10:00:00+03:00")
    assert iso == "2026-06-21T07:00:00+00:00"


def test_anomaly_score_increases_with_change_and_volume(tmp_path):
    service = build_service(tmp_path)

    low = service._anomaly_score(event_type="holder_increased", change_pct=1.0, relative_volume=0.8)
    high = service._anomaly_score(event_type="holder_exited", change_pct=12.0, relative_volume=3.2)

    assert 0 <= low <= 100
    assert 0 <= high <= 100
    assert high > low
