from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import get_market_snapshot_service
from ..schemas import MarketSnapshotResponse
from ..services.market_snapshot import MarketSnapshotService

router = APIRouter(prefix="/api/v1/market", tags=["market"])


@router.get("/snapshot", response_model=MarketSnapshotResponse)
async def market_snapshot(
    service: MarketSnapshotService = Depends(get_market_snapshot_service),
) -> MarketSnapshotResponse:
    snapshot = await service.get_snapshot()
    return MarketSnapshotResponse(
        updated_at_iso=snapshot.updated_at_iso,
        updated_at_local=snapshot.updated_at_local,
        usd_ils=snapshot.usd_ils,
        usd_ils_change_pct=snapshot.usd_ils_change_pct,
        fear_greed_score=snapshot.fear_greed_score,
        fear_greed_rating=snapshot.fear_greed_rating,
        vix=snapshot.vix,
        vix_change_pct=snapshot.vix_change_pct,
        spy_change_pct=snapshot.spy_change_pct,
        qqq_change_pct=snapshot.qqq_change_pct,
        cache_ttl_seconds=snapshot.cache_ttl_seconds,
    )


@router.post("/refresh", response_model=MarketSnapshotResponse)
async def refresh_market_snapshot(
    service: MarketSnapshotService = Depends(get_market_snapshot_service),
) -> MarketSnapshotResponse:
    snapshot = await service.refresh_snapshot()
    return MarketSnapshotResponse(
        updated_at_iso=snapshot.updated_at_iso,
        updated_at_local=snapshot.updated_at_local,
        usd_ils=snapshot.usd_ils,
        usd_ils_change_pct=snapshot.usd_ils_change_pct,
        fear_greed_score=snapshot.fear_greed_score,
        fear_greed_rating=snapshot.fear_greed_rating,
        vix=snapshot.vix,
        vix_change_pct=snapshot.vix_change_pct,
        spy_change_pct=snapshot.spy_change_pct,
        qqq_change_pct=snapshot.qqq_change_pct,
        cache_ttl_seconds=snapshot.cache_ttl_seconds,
    )
