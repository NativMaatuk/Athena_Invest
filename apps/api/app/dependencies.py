from __future__ import annotations

from functools import lru_cache
from typing import Literal

from fastapi import HTTPException, Request, status

from .config import ApiSettings
from .rate_limit import InMemoryRateLimiter
from .services.active_users_service import ActiveUsersService
from .services.analysis_runtime import AnalysisRuntime
from .services.market_snapshot import MarketSnapshotService
from .services.market_snapshot_scheduler import MarketSnapshotScheduler
from .services.perplexity_client import PerplexityClient
from .services.watchlist_service import WatchlistService
from .services.watchlist_scheduler import WatchlistScheduler
from .storage.watchlist_store import WatchlistStore
from .storage.watchlist_store_postgres import PostgresWatchlistStore


@lru_cache(maxsize=1)
def get_settings() -> ApiSettings:
    return ApiSettings.from_env()


@lru_cache(maxsize=1)
def get_runtime() -> AnalysisRuntime:
    return AnalysisRuntime(get_settings())


@lru_cache(maxsize=1)
def get_rate_limiter() -> InMemoryRateLimiter:
    return InMemoryRateLimiter(get_settings().rate_limit_window_seconds)


@lru_cache(maxsize=1)
def get_perplexity_client() -> PerplexityClient:
    return PerplexityClient()


@lru_cache(maxsize=1)
def get_market_snapshot_service() -> MarketSnapshotService:
    settings = get_settings()
    return MarketSnapshotService(
        market_hours_ttl_seconds=settings.market_snapshot_refresh_market_hours_seconds,
        off_hours_ttl_seconds=settings.market_snapshot_refresh_off_hours_seconds,
    )


@lru_cache(maxsize=1)
def get_market_snapshot_scheduler() -> MarketSnapshotScheduler:
    settings = get_settings()
    return MarketSnapshotScheduler(
        service=get_market_snapshot_service(),
        interval_seconds=settings.market_snapshot_refresh_interval_seconds,
    )


@lru_cache(maxsize=1)
def get_active_users_service() -> ActiveUsersService:
    return ActiveUsersService(window_seconds=300)


@lru_cache(maxsize=1)
def get_watchlist_store() -> WatchlistStore:
    settings = get_settings()
    require_postgres = settings.require_postgres_watchlist or settings.is_production
    if require_postgres and not settings.database_url:
        raise RuntimeError(
            "PostgreSQL is required for watchlist in this environment. "
            "Set DATABASE_URL/POSTGRES_URL."
        )
    if settings.database_url:
        return PostgresWatchlistStore(settings.database_url)  # type: ignore[return-value]
    return WatchlistStore(settings.watchlist_db_path)


def get_watchlist_storage_backend() -> Literal["postgres", "sqlite"]:
    settings = get_settings()
    if settings.database_url:
        return "postgres"
    return "sqlite"


@lru_cache(maxsize=1)
def get_watchlist_service() -> WatchlistService:
    settings = get_settings()
    return WatchlistService(
        store=get_watchlist_store(),
        max_items=settings.watchlist_max_items,
        significant_change_pct=settings.watchlist_significant_change_pct,
        degraded_failure_threshold=settings.watchlist_degraded_failure_threshold,
        retention_days=settings.watchlist_retention_days,
    )


@lru_cache(maxsize=1)
def get_watchlist_scheduler() -> WatchlistScheduler:
    settings = get_settings()
    return WatchlistScheduler(
        service=get_watchlist_service(),
        interval_seconds=settings.watchlist_refresh_interval_seconds,
    )


def enforce_rate_limit(request: Request, *, bucket: str, limit: int) -> None:
    client_host = request.client.host if request.client else "unknown"
    key = f"{bucket}:{client_host}"
    if not get_rate_limiter().allow(key, limit):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="יותר מדי בקשות. נסה שוב בעוד דקה.",
        )
