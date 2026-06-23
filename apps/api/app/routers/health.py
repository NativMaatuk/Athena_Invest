from __future__ import annotations

from fastapi import APIRouter

from ..dependencies import get_settings, get_watchlist_storage_backend
from ..schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def healthcheck() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        watchlist_storage_backend=get_watchlist_storage_backend(),
        internal_schedulers_enabled=settings.enable_internal_schedulers,
    )
