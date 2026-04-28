import asyncio
import time

import pytest

from src.domain.analysis_service import AnalysisService
from src.infrastructure.cache.cache_store import TTLCache
from src.shared.errors import ExternalServiceError, RequestTimeoutError, TickerNotFoundError


class FakeMarketDataClient:
    def __init__(self, fail_times=0, fail_message="boom", sleep_seconds=0.0):
        self.fail_times = fail_times
        self.fail_message = fail_message
        self.sleep_seconds = sleep_seconds
        self.fetch_calls = 0
        self.build_calls = 0

    def fetch_analysis_dataframe(self, ticker: str):
        self.fetch_calls += 1
        if self.sleep_seconds:
            time.sleep(self.sleep_seconds)
        if self.fetch_calls <= self.fail_times:
            raise ValueError(self.fail_message)
        return {"rows": [1, 2, 3]}, 12, None

    def build_analysis(self, df, days_until_earnings, next_earnings_date):
        self.build_calls += 1
        return {"is_positive": True, "status": "breakout"}


class FakeTickerInfoClient:
    def __init__(self):
        self.calls = 0

    def get_ticker_info(self, ticker: str):
        self.calls += 1
        return {"sector": "Tech"}


class FakeFormatter:
    def format_analysis(self, ticker: str, analysis: dict) -> str:
        return f"{ticker}:ok"


def build_service(market_client, info_client, timeout=1, retries=1):
    return AnalysisService(
        market_data_client=market_client,
        ticker_info_client=info_client,
        formatter=FakeFormatter(),
        request_timeout_seconds=timeout,
        retry_attempts=retries,
        analysis_cache=TTLCache(60),
        ticker_info_cache=TTLCache(60),
    )


@pytest.mark.asyncio
async def test_analysis_service_uses_cache_for_same_ticker():
    market = FakeMarketDataClient()
    info = FakeTickerInfoClient()
    service = build_service(market, info, timeout=2, retries=0)

    first = await service.analyze_ticker("AAPL")
    second = await service.analyze_ticker("AAPL")

    assert first is second
    assert market.fetch_calls == 1
    assert info.calls == 1


@pytest.mark.asyncio
async def test_analysis_service_deduplicates_in_flight_requests():
    market = FakeMarketDataClient(sleep_seconds=0.1)
    info = FakeTickerInfoClient()
    service = build_service(market, info, timeout=2, retries=0)

    first, second = await asyncio.gather(
        service.analyze_ticker("MSFT"),
        service.analyze_ticker("MSFT"),
    )

    assert first is second
    assert market.fetch_calls == 1
    assert info.calls == 1


@pytest.mark.asyncio
async def test_analysis_service_retries_transient_error_then_succeeds():
    market = FakeMarketDataClient(fail_times=1, fail_message="temporary outage")
    info = FakeTickerInfoClient()
    service = build_service(market, info, timeout=2, retries=1)

    result = await service.analyze_ticker("NVDA")

    assert result.ticker == "NVDA"
    assert market.fetch_calls == 2


@pytest.mark.asyncio
async def test_analysis_service_raises_timeout_after_retries():
    market = FakeMarketDataClient(sleep_seconds=0.2)
    info = FakeTickerInfoClient()
    service = build_service(market, info, timeout=0.05, retries=1)

    with pytest.raises(RequestTimeoutError):
        await service.analyze_ticker("TSLA")

    assert market.fetch_calls >= 1


@pytest.mark.asyncio
async def test_analysis_service_maps_missing_ticker_to_domain_error():
    market = FakeMarketDataClient(
        fail_times=1,
        fail_message="No data found, symbol may be delisted",
    )
    info = FakeTickerInfoClient()
    service = build_service(market, info, timeout=2, retries=3)

    with pytest.raises(TickerNotFoundError):
        await service.analyze_ticker("ZZZZ999")

    # Missing ticker should fail fast without retry loop.
    assert market.fetch_calls == 1


@pytest.mark.asyncio
async def test_analysis_service_wraps_unknown_errors():
    market = FakeMarketDataClient(fail_times=1, fail_message="upstream explosion")
    info = FakeTickerInfoClient()
    service = build_service(market, info, timeout=2, retries=0)

    with pytest.raises(ExternalServiceError):
        await service.analyze_ticker("IBM")
