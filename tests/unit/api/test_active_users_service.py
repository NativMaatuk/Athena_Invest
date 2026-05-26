from __future__ import annotations

from apps.api.app.services.active_users_service import ActiveUsersService


def test_active_users_service_counts_unique_sessions():
    service = ActiveUsersService(window_seconds=300)

    assert service.touch("session-a") == 1
    assert service.touch("session-b") == 2
    assert service.active_count() == 2


def test_active_users_service_expires_stale_sessions(monkeypatch):
    clock = {"now": 1_000.0}

    def fake_time() -> float:
        return clock["now"]

    monkeypatch.setattr("apps.api.app.services.active_users_service.time.time", fake_time)
    service = ActiveUsersService(window_seconds=120)

    service.touch("session-a")
    clock["now"] = 1_060.0
    service.touch("session-b")
    assert service.active_count() == 2

    clock["now"] = 1_130.0
    assert service.active_count() == 1
