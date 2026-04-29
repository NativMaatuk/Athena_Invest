from src.infrastructure.cache.cache_store import TTLCache


def test_cache_returns_value_before_expiry(monkeypatch):
    current_time = 1000.0

    def fake_time():
        return current_time

    monkeypatch.setattr("src.infrastructure.cache.cache_store.time.time", fake_time)
    cache = TTLCache(ttl_seconds=10)
    cache.set("AAPL", {"value": 1})

    assert cache.get("AAPL") == {"value": 1}


def test_cache_expires_and_cleanup_removes_entry(monkeypatch):
    current_time = 1000.0

    def fake_time():
        return current_time

    monkeypatch.setattr("src.infrastructure.cache.cache_store.time.time", fake_time)
    cache = TTLCache(ttl_seconds=10)
    cache.set("AAPL", 123)

    current_time = 1011.0
    assert cache.get("AAPL") is None

    cache.set("MSFT", 1)
    current_time = 1025.0
    cache.cleanup()
    assert cache.get("MSFT") is None
