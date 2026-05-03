from datetime import datetime

import pandas as pd

from agents.classic_analyzer import ClassicAnalyzer


def test_detect_open_gap_marks_partial_when_close_enters_zone():
    analyzer = ClassicAnalyzer()
    df = pd.DataFrame(
        [
            {"Date": datetime(2025, 1, 1), "High": 100.0, "Low": 95.0, "Close": 98.0},
            {"Date": datetime(2025, 1, 2), "High": 110.0, "Low": 105.0, "Close": 108.0},  # gap up
            {"Date": datetime(2025, 1, 3), "High": 112.0, "Low": 106.0, "Close": 106.0},
            {"Date": datetime(2025, 1, 4), "High": 109.0, "Low": 103.0, "Close": 104.0},  # partial fill only
        ]
    )

    gaps = analyzer._detect_open_gaps(df=df, current_price=104.0, lookback=120)

    assert len(gaps) == 1
    assert gaps[0]["direction"] == "up"
    assert gaps[0]["fill_status"] == "partial"
    assert gaps[0]["fill_rule"] == "close"
    assert gaps[0]["zone_low"] == 100.0
    assert gaps[0]["zone_high"] == 105.0


def test_detect_gap_excludes_closed_gap_by_close_rule():
    analyzer = ClassicAnalyzer()
    df = pd.DataFrame(
        [
            {"Date": datetime(2025, 2, 1), "High": 110.0, "Low": 100.0, "Close": 105.0},
            {"Date": datetime(2025, 2, 2), "High": 95.0, "Low": 90.0, "Close": 92.0},  # gap down
            {"Date": datetime(2025, 2, 3), "High": 97.0, "Low": 93.0, "Close": 96.0},  # partial
            {"Date": datetime(2025, 2, 4), "High": 102.0, "Low": 94.0, "Close": 101.0},  # close fill
        ]
    )

    gaps = analyzer._detect_open_gaps(df=df, current_price=101.0, lookback=120)

    assert gaps == []


def test_detect_gap_excludes_gap_closed_by_wick_fill():
    analyzer = ClassicAnalyzer()
    df = pd.DataFrame(
        [
            {"Date": datetime(2025, 2, 1), "High": 100.0, "Low": 95.0, "Close": 99.0},
            {"Date": datetime(2025, 2, 2), "High": 110.0, "Low": 106.0, "Close": 109.0},  # gap up
            {"Date": datetime(2025, 2, 3), "High": 111.0, "Low": 99.8, "Close": 102.0},   # wick closes gap
        ]
    )

    gaps = analyzer._detect_open_gaps(df=df, current_price=102.0, lookback=120)

    assert gaps == []


def test_analyze_classic_includes_gap_summary_fields():
    analyzer = ClassicAnalyzer()
    df = pd.DataFrame(
        [
            {"Date": datetime(2025, 3, 1), "High": 100.0, "Low": 95.0, "Close": 98.0, "SMA_150": 90.0, "ATR": 2.0},
            {"Date": datetime(2025, 3, 2), "High": 111.0, "Low": 106.0, "Close": 109.0, "SMA_150": 91.0, "ATR": 2.0},
            {"Date": datetime(2025, 3, 3), "High": 112.0, "Low": 107.0, "Close": 110.0, "SMA_150": 92.0, "ATR": 2.0},
            {"Date": datetime(2025, 3, 4), "High": 110.0, "Low": 104.0, "Close": 104.0, "SMA_150": 93.0, "ATR": 2.0},
        ]
    )

    analysis = analyzer.analyze_classic(df)

    assert analysis["has_unfilled_gap"] is True
    assert analysis["gap_summary"]["open_count"] >= 1
    assert analysis["gap_summary"]["fill_rule"] == "close"
    assert analysis["nearest_open_gap"] is not None


def test_format_output_does_not_include_gap_text_block():
    analyzer = ClassicAnalyzer()
    analysis = {
        "current_price": 150.0,
        "days_until_earnings": None,
        "next_earnings_date": None,
        "is_positive": True,
        "distance_from_sma": 3.0,
        "entry_zone": {"support": 145.0, "resistance": 155.0},
        "sma_150": 145.0,
        "status": "accumulation",
        "sma_slope": "rising",
        "atr_pct": 2.5,
        "atr_warning": None,
        "is_extended": False,
        "gap_summary": {"open_count": 1, "up_count": 1, "down_count": 0, "fill_rule": "close"},
        "nearest_open_gap": {
            "direction": "up",
            "fill_status": "partial",
            "gap_date": datetime(2025, 4, 1),
            "zone_low": 140.0,
            "zone_high": 145.0,
            "gap_size_pct": 3.2,
            "distance_from_current_pct": 5.1,
        },
    }

    output = analyzer.format_output("AAPL", analysis)

    assert "גאפים פתוחים (לפי Close)" not in output
    assert "גאפ קרוב" not in output
