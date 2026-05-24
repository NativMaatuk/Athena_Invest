from __future__ import annotations

import asyncio
import io
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
import pandas as pd

from ..dependencies import enforce_rate_limit, get_runtime, get_settings
from ..schemas import AnalysisPayload, AnalysisRequest, ChartDataResponse, ChartPoint
from ..serializers import to_analysis_payload
from ..services.analysis_runtime import AnalysisRuntime
from src.domain.ticker_validation import normalize_ticker, validate_ticker
from src.shared.errors import ValidationError

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])


def _normalize_and_validate_ticker(raw: str) -> str:
    ticker = normalize_ticker(raw)
    try:
        validate_ticker(ticker)
    except ValidationError as exc:
        raise ValidationError(str(exc)) from exc
    return ticker


def _safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:  # noqa: BLE001
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_time_string(value) -> str:
    if isinstance(value, (datetime, date)):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    try:
        return pd.to_datetime(text).date().isoformat()
    except Exception:  # noqa: BLE001
        return text


def _serialize_chart_points(df, max_points: int = 260) -> list[ChartPoint]:
    if df is None or len(df) == 0:
        return []
    frame = df.copy()
    if "Date" in frame.columns:
        time_series = frame["Date"]
    elif isinstance(frame.index, pd.DatetimeIndex):
        time_series = frame.index
    else:
        time_series = frame.index
    frame = frame.tail(max_points)
    if len(time_series) >= len(frame):
        time_values = list(time_series)[-len(frame) :]
    else:
        time_values = list(time_series)

    points: list[ChartPoint] = []
    for idx, (_, row) in enumerate(frame.iterrows()):
        open_v = _safe_float(row.get("Open"))
        high_v = _safe_float(row.get("High"))
        low_v = _safe_float(row.get("Low"))
        close_v = _safe_float(row.get("Close"))
        if open_v is None or high_v is None or low_v is None or close_v is None:
            continue
        raw_time = time_values[idx] if idx < len(time_values) else None
        points.append(
            ChartPoint(
                time=_to_time_string(raw_time),
                open=open_v,
                high=high_v,
                low=low_v,
                close=close_v,
                volume=_safe_float(row.get("Volume")),
                sma_150=_safe_float(row.get("SMA_150")),
                bb_upper=_safe_float(row.get("BB_Upper")),
                bb_middle=_safe_float(row.get("BB_Middle")),
                bb_lower=_safe_float(row.get("BB_Lower")),
            )
        )
    return [point for point in points if point.time]


@router.post("", response_model=AnalysisPayload)
async def analyze_ticker(
    payload: AnalysisRequest,
    request: Request,
    runtime: AnalysisRuntime = Depends(get_runtime),
) -> AnalysisPayload:
    settings = get_settings()
    enforce_rate_limit(
        request,
        bucket="analysis",
        limit=settings.rate_limit_analysis_requests,
    )
    ticker = _normalize_and_validate_ticker(payload.ticker)
    result = await runtime.analysis_service.analyze_ticker(ticker)
    return to_analysis_payload(result)


@router.get("/{ticker}/chart")
async def ticker_chart(
    ticker: str,
    request: Request,
    mode: str = "full",
    runtime: AnalysisRuntime = Depends(get_runtime),
) -> StreamingResponse:
    settings = get_settings()
    enforce_rate_limit(
        request,
        bucket="analysis",
        limit=settings.rate_limit_analysis_requests,
    )
    chart_mode = mode if mode in {"full", "gaps_only"} else "full"
    normalized = _normalize_and_validate_ticker(ticker)
    result = await runtime.analysis_service.analyze_ticker(normalized)
    image_buffer = await asyncio.to_thread(
        runtime.chart_notifier.generate_chart_image,
        result.df,
        result.ticker,
        bool(result.analysis.get("is_positive", False)),
        result.analysis,
        chart_mode,
    )
    if not image_buffer:
        raise HTTPException(status_code=404, detail="לא נוצר גרף עבור הטיקר המבוקש.")
    image_buffer.seek(0)
    return StreamingResponse(io.BytesIO(image_buffer.read()), media_type="image/png")


@router.get("/{ticker}/chart-data", response_model=ChartDataResponse)
async def chart_data(
    ticker: str,
    request: Request,
    runtime: AnalysisRuntime = Depends(get_runtime),
) -> ChartDataResponse:
    settings = get_settings()
    enforce_rate_limit(
        request,
        bucket="analysis",
        limit=settings.rate_limit_analysis_requests,
    )
    normalized = _normalize_and_validate_ticker(ticker)
    result = await runtime.analysis_service.analyze_ticker(normalized)
    return ChartDataResponse(
        ticker=result.ticker,
        points=_serialize_chart_points(result.df),
    )
