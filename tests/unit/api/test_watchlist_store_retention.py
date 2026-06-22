from __future__ import annotations

from datetime import datetime, timedelta, timezone

from apps.api.app.storage.watchlist_store import WatchlistStore


def test_prune_old_data_removes_old_snapshots_and_events(tmp_path):
    store = WatchlistStore(str(tmp_path / "watchlist-retention.db"))
    store.add_ticker("NVDA", max_items=5)

    now = datetime.now(timezone.utc).replace(microsecond=0)
    old_iso = (now - timedelta(days=120)).isoformat()
    recent_iso = (now - timedelta(days=3)).isoformat()

    store.insert_snapshot(
        ticker="NVDA",
        captured_at=old_iso,
        institutional_pct=70.0,
        insider_pct=1.2,
        volume_today=1_000_000,
        avg_volume_30d=800_000,
        relative_volume=1.25,
        top_holders=[],
    )
    store.insert_snapshot(
        ticker="NVDA",
        captured_at=recent_iso,
        institutional_pct=71.0,
        insider_pct=1.2,
        volume_today=1_200_000,
        avg_volume_30d=820_000,
        relative_volume=1.46,
        top_holders=[],
    )
    store.insert_event(
        ticker="NVDA",
        event_type="holder_reduced",
        severity="high",
        message="old",
        holder_name="Holder A",
        change_pct=-6.0,
        relative_volume=2.2,
        created_at=old_iso,
    )
    store.insert_event(
        ticker="NVDA",
        event_type="holder_increased",
        severity="medium",
        message="recent",
        holder_name="Holder B",
        change_pct=5.1,
        relative_volume=1.8,
        created_at=recent_iso,
    )

    store.prune_old_data(90)

    history = store.history("NVDA", hours=24 * 365)
    events = store.list_events(since_iso=None, limit=50)

    assert len(history) == 1
    assert history[0]["captured_at"] == recent_iso
    assert len(events) == 1
    assert events[0]["message"] == "recent"
