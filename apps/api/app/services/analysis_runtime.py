from __future__ import annotations

from agents.classic_analyzer import ClassicAnalyzer
from agents.discord_notifier import DiscordNotifier
from agents.ticker_info_agent import TickerInfoAgent
from src.domain.analysis_service import AnalysisService
from src.infrastructure.cache.cache_store import TTLCache
from src.infrastructure.clients.translation_client import TranslationTickerInfoClient
from src.infrastructure.clients.yfinance_client import YFinanceMarketDataClient
from src.presentation.response_formatter import ResponseFormatter

from ..config import ApiSettings
from .ticker_resolver import LightweightTickerResolver

try:
    from src.infrastructure.clients.yfinance_ticker_resolver import YFinanceTickerResolver
except ModuleNotFoundError:  # pragma: no cover
    YFinanceTickerResolver = LightweightTickerResolver  # type: ignore[assignment]


class AnalysisRuntime:
    def __init__(self, settings: ApiSettings):
        analyzer = ClassicAnalyzer()
        ticker_agent = TickerInfoAgent()
        self.analysis_service = AnalysisService(
            market_data_client=YFinanceMarketDataClient(analyzer),
            ticker_info_client=TranslationTickerInfoClient(ticker_agent),
            formatter=ResponseFormatter(analyzer),
            request_timeout_seconds=settings.request_timeout_seconds,
            retry_attempts=settings.retry_attempts,
            analysis_cache=TTLCache(settings.analysis_cache_ttl_seconds),
            ticker_info_cache=TTLCache(settings.ticker_info_cache_ttl_seconds),
        )
        self.chart_notifier = DiscordNotifier(webhook_url=None)
        self.ticker_resolver = YFinanceTickerResolver()
