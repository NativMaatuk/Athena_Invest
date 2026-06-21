from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


def _to_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _to_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class ApiSettings:
    host: str
    port: int
    cors_origins: tuple[str, ...]
    request_timeout_seconds: int
    retry_attempts: int
    analysis_cache_ttl_seconds: int
    ticker_info_cache_ttl_seconds: int
    rate_limit_window_seconds: int
    rate_limit_analysis_requests: int
    rate_limit_chat_requests: int
    database_url: str | None
    enable_internal_schedulers: bool
    market_snapshot_refresh_interval_seconds: int
    watchlist_db_path: str
    watchlist_max_items: int
    watchlist_refresh_interval_seconds: int
    watchlist_significant_change_pct: int
    watchlist_degraded_failure_threshold: int

    @classmethod
    def from_env(cls) -> "ApiSettings":
        load_dotenv()
        raw_origins = os.getenv("WEB_API_CORS_ORIGINS", "http://localhost:3000")
        cors_origins = tuple(origin.strip() for origin in raw_origins.split(",") if origin.strip())
        return cls(
            host=os.getenv("WEB_API_HOST", "0.0.0.0"),
            port=_to_int("WEB_API_PORT", 8000),
            cors_origins=cors_origins or ("http://localhost:3000",),
            request_timeout_seconds=_to_int("WEB_API_REQUEST_TIMEOUT_SECONDS", 20),
            retry_attempts=_to_int("WEB_API_RETRY_ATTEMPTS", 1),
            analysis_cache_ttl_seconds=_to_int("WEB_API_ANALYSIS_CACHE_TTL_SECONDS", 180),
            ticker_info_cache_ttl_seconds=_to_int("WEB_API_TICKER_INFO_CACHE_TTL_SECONDS", 86400),
            rate_limit_window_seconds=_to_int("WEB_API_RATE_LIMIT_WINDOW_SECONDS", 60),
            rate_limit_analysis_requests=_to_int("WEB_API_RATE_LIMIT_ANALYSIS_REQUESTS", 20),
            rate_limit_chat_requests=_to_int("WEB_API_RATE_LIMIT_CHAT_REQUESTS", 12),
            database_url=os.getenv("DATABASE_URL"),
            enable_internal_schedulers=_to_bool("WEB_API_ENABLE_INTERNAL_SCHEDULERS", True),
            market_snapshot_refresh_interval_seconds=_to_int("WEB_API_MARKET_REFRESH_INTERVAL_SECONDS", 300),
            watchlist_db_path=os.getenv("WEB_API_WATCHLIST_DB_PATH", "data/watchlist.db"),
            watchlist_max_items=_to_int("WEB_API_WATCHLIST_MAX_ITEMS", 5),
            watchlist_refresh_interval_seconds=_to_int("WEB_API_WATCHLIST_REFRESH_INTERVAL_SECONDS", 3600),
            watchlist_significant_change_pct=_to_int("WEB_API_WATCHLIST_SIGNIFICANT_CHANGE_PCT", 5),
            watchlist_degraded_failure_threshold=_to_int("WEB_API_WATCHLIST_DEGRADED_FAILURE_THRESHOLD", 3),
        )
