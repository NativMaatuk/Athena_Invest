import argparse
import asyncio
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.classic_analyzer import ClassicAnalyzer
from agents.ticker_info_agent import TickerInfoAgent
from src.domain.analysis_service import AnalysisService
from src.infrastructure.cache.cache_store import TTLCache
from src.infrastructure.clients.translation_client import TranslationTickerInfoClient
from src.infrastructure.clients.yfinance_client import YFinanceMarketDataClient
from src.presentation.response_formatter import ResponseFormatter


REQUEST_MATRIX = [
    "AAPL",
    "MSFT",
    "NVDA",
    "TSLA",
    "AMZN",
    "AAPL",
    "MSFT",
    "NVDA",
    "ZZZZ9999",
    "1234",
]


@dataclass
class Profile:
    name: str
    timeout_seconds: int
    retry_attempts: int
    max_concurrent: int


PROFILES = [
    Profile("A_baseline", timeout_seconds=15, retry_attempts=1, max_concurrent=3),
    Profile("B_timeout10", timeout_seconds=10, retry_attempts=1, max_concurrent=3),
    Profile("C_timeout10_conc4", timeout_seconds=10, retry_attempts=1, max_concurrent=4),
    Profile("D_timeout8_conc4", timeout_seconds=8, retry_attempts=1, max_concurrent=4),
]


def build_service(profile: Profile) -> AnalysisService:
    analyzer = ClassicAnalyzer()
    ticker_agent = TickerInfoAgent()
    return AnalysisService(
        market_data_client=YFinanceMarketDataClient(analyzer),
        ticker_info_client=TranslationTickerInfoClient(ticker_agent),
        formatter=ResponseFormatter(analyzer),
        request_timeout_seconds=profile.timeout_seconds,
        retry_attempts=profile.retry_attempts,
        analysis_cache=TTLCache(180),
        ticker_info_cache=TTLCache(86400),
    )


async def run_profile(profile: Profile, tickers: list[str]) -> dict:
    service = build_service(profile)
    semaphore = asyncio.Semaphore(profile.max_concurrent)
    latencies = []
    success_count = 0
    error_count = 0

    async def run_single(ticker: str):
        nonlocal success_count, error_count
        started = time.perf_counter()
        async with semaphore:
            try:
                await service.analyze_ticker(ticker)
                success_count += 1
            except Exception:  # noqa: BLE001
                error_count += 1
            finally:
                latencies.append((time.perf_counter() - started) * 1000)

    await asyncio.gather(*(run_single(ticker) for ticker in tickers))
    avg_ms = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
    p95_ms = round(statistics.quantiles(latencies, n=100)[94], 2) if len(latencies) >= 2 else avg_ms
    return {
        "profile": profile.name,
        "timeout_seconds": profile.timeout_seconds,
        "retry_attempts": profile.retry_attempts,
        "max_concurrent": profile.max_concurrent,
        "success_count": success_count,
        "error_count": error_count,
        "avg_latency_ms": avg_ms,
        "p95_latency_ms": p95_ms,
    }


def choose_candidate(results: list[dict]) -> str:
    baseline = next((r for r in results if r["profile"] == "A_baseline"), None)
    if not baseline:
        return "No baseline result found."

    for result in results:
        if result["profile"] == "A_baseline":
            continue
        if (
            result["p95_latency_ms"] < baseline["p95_latency_ms"]
            and result["error_count"] <= baseline["error_count"]
        ):
            return result["profile"]
    return "No candidate beat baseline under safety criteria."


async def main():
    parser = argparse.ArgumentParser(description="Run profile-based analysis latency benchmark.")
    parser.add_argument(
        "--requests",
        type=int,
        default=len(REQUEST_MATRIX),
        help="How many requests from matrix to use.",
    )
    args = parser.parse_args()

    tickers = REQUEST_MATRIX[: args.requests]
    results = []
    for profile in PROFILES:
        print(f"Running profile: {profile.name}")
        result = await run_profile(profile, tickers)
        results.append(result)

    print("\n| profile | timeout | retry | max_concurrent | success | error | avg_ms | p95_ms |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    for result in results:
        print(
            f"| {result['profile']} | {result['timeout_seconds']} | {result['retry_attempts']} "
            f"| {result['max_concurrent']} | {result['success_count']} | {result['error_count']} "
            f"| {result['avg_latency_ms']} | {result['p95_latency_ms']} |"
        )

    print(f"\nRecommended candidate: {choose_candidate(results)}")


if __name__ == "__main__":
    asyncio.run(main())
