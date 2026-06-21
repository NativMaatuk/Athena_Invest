from __future__ import annotations

import io
from dataclasses import dataclass

import pandas as pd
from fastapi.testclient import TestClient

from apps.api.app.dependencies import get_perplexity_client, get_runtime, get_watchlist_service
from apps.api.app.main import create_app
from apps.api.app.schemas import PerplexityCitation
from apps.api.app.services.watchlist_service import RefreshSummary
from src.domain.analysis_service import AnalysisResult
from src.shared.errors import TickerNotFoundError


class FakeAnalysisService:
    async def analyze_ticker(self, ticker: str) -> AnalysisResult:
        if ticker == "APPL":
            raise TickerNotFoundError("Ticker 'APPL' could not be found.")
        df = pd.DataFrame(
            {
                "Date": pd.to_datetime(["2026-05-20", "2026-05-21", "2026-05-22"]),
                "Open": [100.0, 102.0, 101.5],
                "High": [103.0, 104.5, 103.2],
                "Low": [99.5, 101.1, 100.7],
                "Close": [102.5, 101.8, 102.9],
                "Volume": [1000000, 1200000, 1100000],
                "SMA_150": [98.0, 98.2, 98.3],
                "BB_Upper": [105.0, 105.2, 105.4],
                "BB_Middle": [101.0, 101.1, 101.2],
                "BB_Lower": [97.0, 97.2, 97.4],
            }
        )
        return AnalysisResult(
            ticker=ticker,
            output_text="🎯 איתות כניסה\nסטטוס נוכחי: Breakout\nרמת סיכון: בינונית",
            analysis={
                "is_positive": True,
                "daily_change_pct": 1.2,
                "gap_summary": {"open_count": 1},
                "open_gaps": [{"zone_low": 100.0, "zone_high": 102.0}],
            },
            info={"sector": "Tech", "industry": "Software", "summary": "Company summary"},
            df=df,
        )


class FakeChartNotifier:
    def generate_chart_image(self, *_args, **_kwargs):
        return io.BytesIO(b"fake-png")


class FakeResolver:
    def suggest(self, _query: str, max_candidates: int = 5):
        @dataclass
        class Item:
            symbol: str
            name: str
            exchange: str
            currency: str
            summary: str
            score: float

        return [
            Item("AAPL", "Apple Inc.", "NMS", "USD", "Consumer electronics", 99.0)
        ][:max_candidates]


class FakeRuntime:
    def __init__(self):
        self.analysis_service = FakeAnalysisService()
        self.chart_notifier = FakeChartNotifier()
        self.ticker_resolver = FakeResolver()


class FakePerplexityClient:
    async def ask(self, **_kwargs):
        return "תשובה לדוגמה", [PerplexityCitation(title="Example", url="https://example.com")], "sonar-pro"


class FakeWatchlistService:
    def __init__(self):
        self.items = [
            {
                "ticker": "NVDA",
                "added_at": "2026-01-01T00:00:00+00:00",
                "last_refreshed_at": "2026-01-01T01:00:00+00:00",
                "is_degraded": False,
                "last_error": None,
                "latest_snapshot": {
                    "id": 1,
                    "ticker": "NVDA",
                    "captured_at": "2026-01-01T01:00:00+00:00",
                    "institutional_pct": 66.1,
                    "insider_pct": 1.2,
                    "volume_today": 1000000,
                    "avg_volume_30d": 700000,
                    "relative_volume": 1.43,
                    "top_holders": [{"name": "BlackRock", "pct_out": 7.0, "pct_out_text": "7.00%"}],
                    "fetch_status": "ok",
                    "error_message": None,
                },
            }
        ]

    @property
    def max_items(self) -> int:
        return 5

    def list_watchlist(self):
        return {"max_items": 5, "last_refresh_at": "2026-01-01T01:00:00+00:00", "items": self.items}

    def add_ticker(self, ticker: str):
        self.items.append(
            {
                "ticker": ticker,
                "added_at": "2026-01-01T02:00:00+00:00",
                "last_refreshed_at": None,
                "is_degraded": False,
                "last_error": None,
                "latest_snapshot": None,
            }
        )
        return self.list_watchlist()

    def remove_ticker(self, ticker: str):
        self.items = [item for item in self.items if item["ticker"] != ticker]
        return self.list_watchlist()

    def get_history(self, ticker: str, *, hours: int):
        _ = hours
        return [
            {
                "id": 2,
                "ticker": ticker,
                "captured_at": "2026-01-01T00:00:00+00:00",
                "institutional_pct": 65.0,
                "insider_pct": 1.1,
                "volume_today": 900000,
                "avg_volume_30d": 700000,
                "relative_volume": 1.28,
                "top_holders": [],
                "fetch_status": "ok",
                "error_message": None,
            }
        ]

    def parse_since(self, since: str | None):
        return since

    def get_events(self, *, since_iso: str | None, limit: int):
        _ = since_iso
        _ = limit
        return [
            {
                "id": 10,
                "ticker": "NVDA",
                "event_type": "holder_reduced",
                "severity": "high",
                "message": "NVDA: BlackRock הקטין/ה החזקה ב-5.10%.",
                "holder_name": "BlackRock",
                "change_pct": -5.1,
                "relative_volume": 2.1,
                "created_at": "2026-01-01T03:00:00+00:00",
            }
        ]

    def refresh_watchlist(self):
        return RefreshSummary(refreshed=1, failures=0, events_created=1)


def build_client() -> TestClient:
    app = create_app()
    watchlist_service = FakeWatchlistService()
    app.dependency_overrides[get_runtime] = lambda: FakeRuntime()
    app.dependency_overrides[get_perplexity_client] = lambda: FakePerplexityClient()
    app.dependency_overrides[get_watchlist_service] = lambda: watchlist_service
    return TestClient(app)


def test_health_route():
    client = build_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analysis_route_returns_payload():
    client = build_client()
    response = client.post("/api/v1/analysis", json={"ticker": "aapl"})
    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "AAPL"
    assert body["daily_change_pct"] == 1.2
    assert body["gap_summary"]["open_count"] == 1


def test_analysis_unknown_ticker_returns_structured_error():
    client = build_client()
    response = client.post("/api/v1/analysis", json={"ticker": "appl"})
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "TICKER_NOT_FOUND"
    assert body["error"]["request_id"]


def test_chart_route_returns_png():
    client = build_client()
    response = client.get("/api/v1/analysis/AAPL/chart?mode=full")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")


def test_chart_data_route_returns_points():
    client = build_client()
    response = client.get("/api/v1/analysis/AAPL/chart-data")
    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "AAPL"
    assert len(body["points"]) >= 1
    assert body["points"][0]["open"] > 0


def test_suggestions_route():
    client = build_client()
    response = client.get("/api/v1/ticker/suggest?q=aapl")
    assert response.status_code == 200
    body = response.json()
    assert body["suggestions"][0]["symbol"] == "AAPL"


def test_perplexity_chat_route():
    client = build_client()
    response = client.post(
        "/api/v1/chat/perplexity",
        json={"question": "מה מצב המניה?", "api_key": "test-key-1234567890"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"]
    assert body["model"] == "sonar-pro"


def test_presence_routes():
    client = build_client()
    heartbeat = client.post("/api/v1/presence/heartbeat", json={"session_id": "session-test-123"})
    assert heartbeat.status_code == 200
    heartbeat_body = heartbeat.json()
    assert heartbeat_body["active_users"] >= 1

    count = client.get("/api/v1/presence/active-users")
    assert count.status_code == 200
    count_body = count.json()
    assert count_body["active_users"] >= 1
    assert count_body["window_seconds"] == 300


def test_watchlist_routes():
    client = build_client()

    listing = client.get("/api/v1/watchlist")
    assert listing.status_code == 200
    assert listing.json()["items"][0]["ticker"] == "NVDA"

    add = client.post("/api/v1/watchlist", json={"ticker": "AAPL"})
    assert add.status_code == 200
    assert any(item["ticker"] == "AAPL" for item in add.json()["items"])

    history = client.get("/api/v1/watchlist/NVDA/history?hours=48")
    assert history.status_code == 200
    assert history.json()["ticker"] == "NVDA"
    assert len(history.json()["snapshots"]) >= 1

    events = client.get("/api/v1/watchlist/events/feed?limit=10")
    assert events.status_code == 200
    assert events.json()["events"][0]["event_type"] == "holder_reduced"

    refresh = client.post("/api/v1/watchlist/refresh")
    assert refresh.status_code == 200
    assert refresh.json()["refreshed"] == 1

    removed = client.delete("/api/v1/watchlist/NVDA")
    assert removed.status_code == 200
    assert not any(item["ticker"] == "NVDA" for item in removed.json()["items"])
