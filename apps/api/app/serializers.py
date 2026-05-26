from __future__ import annotations

from datetime import date, datetime

from src.domain.analysis_service import AnalysisResult

from .schemas import AnalysisPayload, CompanyProfile


def _extract_first_matching_line(text: str, markers: tuple[str, ...]) -> str | None:
    for line in text.splitlines():
        normalized = line.strip().replace("*", "")
        if not normalized:
            continue
        if any(marker in normalized for marker in markers):
            return normalized
    return None


def _to_json_safe(value):
    """Recursively convert numpy/pandas/scalar values to JSON-safe Python types."""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _to_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_json_safe(item) for item in value]

    # numpy/pandas scalars commonly expose item().
    item_method = getattr(value, "item", None)
    if callable(item_method):
        try:
            return _to_json_safe(item_method())
        except Exception:  # noqa: BLE001
            pass

    # pandas timestamps typically expose isoformat().
    iso_method = getattr(value, "isoformat", None)
    if callable(iso_method):
        try:
            return iso_method()
        except Exception:  # noqa: BLE001
            pass

    return str(value)


def _resolve_daily_change_pct(analysis: dict) -> float | None:
    raw = analysis.get("daily_change_pct")
    try:
        if raw is not None:
            return float(raw)
    except (TypeError, ValueError):
        pass

    current_price = analysis.get("current_price")
    previous_close = analysis.get("previous_close")
    try:
        if current_price is None or previous_close in (None, 0):
            return None
        return ((float(current_price) - float(previous_close)) / float(previous_close)) * 100
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def to_analysis_payload(result: AnalysisResult) -> AnalysisPayload:
    analysis = result.analysis or {}
    info = result.info or {}
    output_text = result.output_text or ""
    return AnalysisPayload(
        ticker=result.ticker,
        formatted_text_he=output_text,
        is_positive=bool(analysis.get("is_positive", False)),
        daily_change_pct=_resolve_daily_change_pct(analysis),
        technical_signal=_extract_first_matching_line(output_text, ("🎯", "⛔")),
        status=_extract_first_matching_line(output_text, ("סטטוס נוכחי",)),
        risk=_extract_first_matching_line(output_text, ("רמת סיכון", "אזהרת סיכון")),
        gap_summary=_to_json_safe(analysis.get("gap_summary") or {}),
        nearest_open_gap=_to_json_safe(analysis.get("nearest_open_gap")),
        open_gaps=_to_json_safe(analysis.get("open_gaps") or []),
        ownership=_to_json_safe(info.get("ownership")),
        company_profile=CompanyProfile(
            sector=_to_json_safe(info.get("sector")),
            industry=_to_json_safe(info.get("industry")),
            summary=_to_json_safe(info.get("summary")),
            market_cap=_to_json_safe(info.get("market_cap")),
        ),
        analysis_raw=_to_json_safe(analysis),
    )
