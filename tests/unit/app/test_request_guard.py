from src.app.request_guard import RequestGuard


def test_request_guard_blocks_during_cooldown(monkeypatch):
    current_time = 1000.0

    def fake_time():
        return current_time

    monkeypatch.setattr("src.app.request_guard.time.time", fake_time)
    guard = RequestGuard(cooldown_seconds=20)

    allowed, remaining = guard.can_process(user_id=1)
    assert allowed is True
    assert remaining == 0

    current_time = 1005.0
    allowed, remaining = guard.can_process(user_id=1)
    assert allowed is False
    assert remaining >= 1


def test_request_guard_allows_after_cooldown(monkeypatch):
    current_time = 1000.0

    def fake_time():
        return current_time

    monkeypatch.setattr("src.app.request_guard.time.time", fake_time)
    guard = RequestGuard(cooldown_seconds=20)

    guard.can_process(user_id=7)
    current_time = 1021.0
    allowed, remaining = guard.can_process(user_id=7)
    assert allowed is True
    assert remaining == 0
