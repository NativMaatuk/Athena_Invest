from __future__ import annotations

import io
from dataclasses import dataclass

import pandas as pd
from fastapi.testclient import TestClient

from apps.api.app.dependencies import get_perplexity_client, get_runtime
from apps.api.app.main import create_app
from apps.api.app.schemas import PerplexityCitation
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


def build_client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_runtime] = lambda: FakeRuntime()
    app.dependency_overrides[get_perplexity_client] = lambda: FakePerplexityClient()
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
