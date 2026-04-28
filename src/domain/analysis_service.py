import asyncio
import time
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from src.infrastructure.cache.cache_store import TTLCache
from src.shared.errors import (
    ExternalServiceError,
    RequestTimeoutError,
    TickerNotFoundError,
)


@dataclass
class AnalysisResult:
    ticker: str
    output_text: str
    analysis: dict
    info: dict
    df: object


@runtime_checkable
class MarketDataClientProtocol(Protocol):
    def fetch_analysis_dataframe(self, ticker: str):
        ...

    def build_analysis(self, df, days_until_earnings, next_earnings_date):
        ...


@runtime_checkable
class TickerInfoClientProtocol(Protocol):
    def get_ticker_info(self, ticker: str) -> dict:
        ...


@runtime_checkable
class ResponseFormatterProtocol(Protocol):
    def format_analysis(self, ticker: str, analysis: dict) -> str:
        ...


class AnalysisService:
    """Orchestrates ticker analysis with timeout, retry, cache and dedup."""

    def __init__(
        self,
        market_data_client: MarketDataClientProtocol,
        ticker_info_client: TickerInfoClientProtocol,
        formatter: ResponseFormatterProtocol,
        request_timeout_seconds: int,
        retry_attempts: int,
        analysis_cache: TTLCache[AnalysisResult],
        ticker_info_cache: TTLCache[dict],
    ):
        self._market_data_client = market_data_client
        self._ticker_info_client = ticker_info_client
        self._formatter = formatter
        self._request_timeout_seconds = request_timeout_seconds
        self._retry_attempts = retry_attempts
        self._analysis_cache = analysis_cache
        self._ticker_info_cache = ticker_info_cache
        self._in_flight: dict[str, asyncio.Future] = {}
        self._in_flight_lock = asyncio.Lock()

    async def analyze_ticker(self, ticker: str) -> AnalysisResult:
        cached = self._analysis_cache.get(ticker)
        if cached:
            return cached

        async with self._in_flight_lock:
            existing = self._in_flight.get(ticker)
            if existing:
                return await existing

            loop = asyncio.get_running_loop()
            future = loop.create_task(self._compute_analysis(ticker))
            self._in_flight[ticker] = future

        try:
            result = await future
            self._analysis_cache.set(ticker, result)
            return result
        finally:
            async with self._in_flight_lock:
                self._in_flight.pop(ticker, None)

    async def _compute_analysis(self, ticker: str) -> AnalysisResult:
        df, days_until_earnings, next_earnings_date = await self._run_blocking_with_retry(
            self._market_data_client.fetch_analysis_dataframe, ticker
        )

        try:
            analysis = self._market_data_client.build_analysis(
                df, days_until_earnings, next_earnings_date
            )
        except Exception as exc:  # noqa: BLE001
            if self._is_missing_ticker_error(exc):
                raise TickerNotFoundError(
                    f"Ticker '{ticker}' could not be found."
                ) from exc
            raise
        analysis["ticker"] = ticker
        output_text = self._formatter.format_analysis(ticker, analysis)

        info = self._ticker_info_cache.get(ticker)
        if info is None:
            info = await self._run_blocking_with_retry(self._ticker_info_client.get_ticker_info, ticker)
            self._ticker_info_cache.set(ticker, info)

        return AnalysisResult(
            ticker=ticker,
            output_text=output_text,
            analysis=analysis,
            info=info,
            df=df,
        )

    async def _run_blocking_with_retry(self, func, *args):
        last_error = None
        for attempt in range(self._retry_attempts + 1):
            start = time.perf_counter()
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(func, *args),
                    timeout=self._request_timeout_seconds,
                )
            except asyncio.TimeoutError as exc:
                last_error = RequestTimeoutError(
                    f"Timeout after {self._request_timeout_seconds}s for {func.__name__}"
                )
            except Exception as exc:  # noqa: BLE001
                if self._is_missing_ticker_error(exc):
                    raise TickerNotFoundError(
                        f"Ticker '{args[0] if args else ''}' could not be found."
                    ) from exc
                last_error = ExternalServiceError(f"{func.__name__} failed: {exc}")

            if attempt < self._retry_attempts:
                elapsed = time.perf_counter() - start
                backoff = max(0.25, min(1.5, elapsed / 2))
                await asyncio.sleep(backoff)

        raise last_error or ExternalServiceError(f"{func.__name__} failed without error")

    @staticmethod
    def _is_missing_ticker_error(exc: Exception) -> bool:
        text = str(exc).lower()
        signals = (
            "quote not found",
            "no data found",
            "symbol may be delisted",
            "possibly delisted",
            "insufficient data points: 0",
            "dataframe is empty",
            "ticker is empty",
            "ticker format is invalid",
        )
        return any(signal in text for signal in signals)
