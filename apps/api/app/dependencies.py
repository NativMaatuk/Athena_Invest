from __future__ import annotations

from functools import lru_cache

from fastapi import HTTPException, Request, status

from .config import ApiSettings
from .rate_limit import InMemoryRateLimiter
from .services.active_users_service import ActiveUsersService
from .services.analysis_runtime import AnalysisRuntime
from .services.market_snapshot import MarketSnapshotService
from .services.perplexity_client import PerplexityClient


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
    return MarketSnapshotService(cache_ttl_seconds=300)


@lru_cache(maxsize=1)
def get_active_users_service() -> ActiveUsersService:
    return ActiveUsersService(window_seconds=300)


def enforce_rate_limit(request: Request, *, bucket: str, limit: int) -> None:
    client_host = request.client.host if request.client else "unknown"
    key = f"{bucket}:{client_host}"
    if not get_rate_limiter().allow(key, limit):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="יותר מדי בקשות. נסה שוב בעוד דקה.",
        )
