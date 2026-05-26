from __future__ import annotations

from datetime import datetime

import numpy as np
from src.domain.analysis_service import AnalysisResult

from apps.api.app.serializers import to_analysis_payload


def test_to_analysis_payload_maps_key_fields():
    result = AnalysisResult(
        ticker="AAPL",
        output_text="🎯 איתות כניסה\nסטטוס נוכחי: Breakout\nרמת סיכון: בינונית",
        analysis={
            "is_positive": True,
            "daily_change_pct": 1.25,
            "gap_summary": {"open_count": 2},
            "open_gaps": [{"zone_low": 180.0, "zone_high": 184.0}],
        },
        info={
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "summary": "Apple designs and sells hardware.",
            "market_cap": "$2T",
            "ownership": {"institutional_pct": 61.4},
        },
        df=None,
    )

    payload = to_analysis_payload(result)

    assert payload.ticker == "AAPL"
    assert payload.is_positive is True
    assert payload.daily_change_pct == 1.25
    assert payload.gap_summary["open_count"] == 2
    assert payload.technical_signal is not None
    assert payload.status is not None
    assert payload.risk is not None
    assert payload.company_profile.sector == "Technology"


def test_to_analysis_payload_normalizes_numpy_scalars():
    result = AnalysisResult(
        ticker="NVDA",
        output_text="🎯 איתות כניסה",
        analysis={
            "is_positive": np.bool_(True),
            "gap_summary": {"open_count": np.int64(1)},
            "open_gaps": [{"is_open": np.bool_(True), "distance": np.float64(2.4)}],
            "created_at": datetime(2026, 1, 1, 8, 0, 0),
        },
        info={"ownership": {"institutional_pct": np.float64(74.1)}},
        df=None,
    )

    payload = to_analysis_payload(result)

    assert payload.is_positive is True
    assert isinstance(payload.gap_summary["open_count"], int)
    assert isinstance(payload.open_gaps[0]["is_open"], bool)
    assert isinstance(payload.analysis_raw["created_at"], str)


def test_to_analysis_payload_computes_daily_change_when_missing():
    result = AnalysisResult(
        ticker="MSFT",
        output_text="",
        analysis={
            "is_positive": True,
            "current_price": 105.0,
            "previous_close": 100.0,
            "gap_summary": {},
            "open_gaps": [],
        },
        info={},
        df=None,
    )

    payload = to_analysis_payload(result)

    assert payload.daily_change_pct == 5.0
