from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from src.domain.ticker_validation import normalize_ticker, validate_ticker
from src.shared.errors import ValidationError

from ..dependencies import enforce_rate_limit, get_settings, get_watchlist_service
from ..schemas import (
    WatchlistAddRequest,
    WatchlistEventsResponse,
    WatchlistHistoryResponse,
    WatchlistListResponse,
    WatchlistRefreshResponse,
)
from ..services.watchlist_service import WatchlistService

router = APIRouter(prefix="/api/v1/watchlist", tags=["watchlist"])


def _normalize_and_validate_ticker(raw: str) -> str:
    ticker = normalize_ticker(raw)
    try:
        validate_ticker(ticker)
    except ValidationError as exc:
        raise ValidationError(str(exc)) from exc
    return ticker


@router.get("", response_model=WatchlistListResponse)
async def list_watchlist(
    request: Request,
    service: WatchlistService = Depends(get_watchlist_service),
) -> WatchlistListResponse:
    settings = get_settings()
    enforce_rate_limit(
        request,
        bucket="analysis",
        limit=settings.rate_limit_analysis_requests,
    )
    payload = await asyncio.to_thread(service.list_watchlist)
    return WatchlistListResponse.model_validate(payload)


@router.post("", response_model=WatchlistListResponse)
async def add_watchlist_ticker(
    body: WatchlistAddRequest,
    request: Request,
    service: WatchlistService = Depends(get_watchlist_service),
) -> WatchlistListResponse:
    settings = get_settings()
    enforce_rate_limit(
        request,
        bucket="analysis",
        limit=settings.rate_limit_analysis_requests,
    )
    ticker = _normalize_and_validate_ticker(body.ticker)
    try:
        payload = await asyncio.to_thread(service.add_ticker, ticker)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return WatchlistListResponse.model_validate(payload)


@router.delete("/{ticker}", response_model=WatchlistListResponse)
async def remove_watchlist_ticker(
    ticker: str,
    request: Request,
    service: WatchlistService = Depends(get_watchlist_service),
) -> WatchlistListResponse:
    settings = get_settings()
    enforce_rate_limit(
        request,
        bucket="analysis",
        limit=settings.rate_limit_analysis_requests,
    )
    normalized = _normalize_and_validate_ticker(ticker)
    try:
        payload = await asyncio.to_thread(service.remove_ticker, normalized)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return WatchlistListResponse.model_validate(payload)


@router.get("/{ticker}/history", response_model=WatchlistHistoryResponse)
async def watchlist_history(
    ticker: str,
    request: Request,
    hours: int = Query(default=168, ge=1, le=24 * 90),
    service: WatchlistService = Depends(get_watchlist_service),
) -> WatchlistHistoryResponse:
    settings = get_settings()
    enforce_rate_limit(
        request,
        bucket="analysis",
        limit=settings.rate_limit_analysis_requests,
    )
    normalized = _normalize_and_validate_ticker(ticker)
    snapshots = await asyncio.to_thread(service.get_history, normalized, hours=hours)
    return WatchlistHistoryResponse(ticker=normalized, snapshots=snapshots)


@router.get("/events/feed", response_model=WatchlistEventsResponse)
async def watchlist_events(
    request: Request,
    since: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    service: WatchlistService = Depends(get_watchlist_service),
) -> WatchlistEventsResponse:
    settings = get_settings()
    enforce_rate_limit(
        request,
        bucket="analysis",
        limit=settings.rate_limit_analysis_requests,
    )
    try:
        since_iso = service.parse_since(since)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="פורמט since אינו תקין.") from exc
    events = await asyncio.to_thread(service.get_events, since_iso=since_iso, limit=limit)
    return WatchlistEventsResponse(events=events)


@router.post("/refresh", response_model=WatchlistRefreshResponse)
async def refresh_watchlist(
    request: Request,
    service: WatchlistService = Depends(get_watchlist_service),
) -> WatchlistRefreshResponse:
    settings = get_settings()
    enforce_rate_limit(
        request,
        bucket="analysis",
        limit=settings.rate_limit_analysis_requests,
    )
    summary = await asyncio.to_thread(service.refresh_watchlist)
    return WatchlistRefreshResponse(
        refreshed=summary.refreshed,
        failures=summary.failures,
        events_created=summary.events_created,
    )
