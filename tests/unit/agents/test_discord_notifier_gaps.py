from datetime import datetime, timedelta

import pandas as pd
import pytest

from agents import discord_notifier
from agents.discord_notifier import ClassicAnalysisNotifier


def test_create_analysis_embed_includes_gap_field():
    notifier = ClassicAnalysisNotifier(webhook_url="https://example.com/webhook")
    content = "\n".join(
        [
            "**NVDA** - 120.00$",
            "\u200f📅 03.05.2026 יום ראשון",
            "\u200f🎯 אזור כניסה טכני: 115.00$ - 125.00$",
            "\u200f🚀 סטטוס נוכחי: פריצה",
            "\u200f✅ רמת סיכון: ATR תקין (2.4%) - תנודתיות רגילה.",
            "\u200f🕳️ גאפים פתוחים (לפי Close): 2 | עליות: 1 | ירידות: 1",
            "\u200f🧭 גאפ קרוב: Gap Up (נסגר חלקית) מתאריך 01.05.2026, טווח 111.00$-114.00$, גודל 2.20%, מרחק נוכחי 4.3%.",
            "\u200f📈 הוראה: איסוף",
            "\u200fהמניה בפריצה מעל הממוצע עם שיפוע חיובי - מגמה עולה.",
        ]
    )

    embed = notifier.create_analysis_embed(
        ticker="NVDA",
        content=content,
        is_positive=True,
        sector="Technology",
        industry="Semiconductors",
    )

    gap_fields = [field for field in embed.get("fields", []) if field.get("name") == "🕳️ גאפים"]
    assert len(gap_fields) == 1
    assert "גאפים פתוחים" in gap_fields[0]["value"]
    assert "גאפ קרוב" in gap_fields[0]["value"]


def test_generate_gap_only_chart_handles_series_date_indexing():
    if not discord_notifier.HAS_MATPLOTLIB:
        pytest.skip("matplotlib not installed")

    notifier = ClassicAnalysisNotifier(webhook_url="https://example.com/webhook")
    base = datetime(2026, 1, 1)
    rows = []
    price = 100.0
    for i in range(40):
        open_price = price + (0.2 if i % 2 == 0 else -0.1)
        close_price = open_price + (0.3 if i % 3 else -0.2)
        high = max(open_price, close_price) + 0.5
        low = min(open_price, close_price) - 0.5
        rows.append(
            {
                "Date": base + timedelta(days=i),
                "Open": open_price,
                "High": high,
                "Low": low,
                "Close": close_price,
                "Volume": 1_000_000 + i * 1000,
            }
        )
        price = close_price

    df = pd.DataFrame(rows)
    analysis = {
        "open_gaps": [
            {
                "direction": "up",
                "gap_date": rows[-5]["Date"],
                "zone_low": rows[-6]["High"],
                "zone_high": rows[-5]["Low"],
                "gap_size_pct": 0.42,
            }
        ],
        "is_positive": True,
    }
    image = notifier.generate_chart_image(
        df=df,
        ticker="SPY",
        is_positive=True,
        analysis=analysis,
        chart_mode="gaps_only",
    )
    assert image is not None


def test_create_ownership_embed_contains_summary_and_holders():
    notifier = ClassicAnalysisNotifier(webhook_url="https://example.com/webhook")
    ownership = {
        "institutional_pct": 68.23,
        "insider_pct": 1.12,
        "top_holders": [
            {"name": "Vanguard", "pct_out": "8.15%", "shares": "512.00M"},
            {"name": "BlackRock", "pct_out": "6.90%", "shares": "433.00M"},
        ],
    }

    embed = notifier.create_ownership_embed(
        ticker="AAPL",
        ownership=ownership,
        is_positive=True,
    )

    assert "בעלות מוסדית" in embed["title"]
    field_names = [field["name"] for field in embed["fields"]]
    assert "בעלות כללית" in field_names
    assert "מחזיקים מובילים" in field_names


def test_create_gap_focus_embed_contains_only_gap_sections():
    notifier = ClassicAnalysisNotifier(webhook_url="https://example.com/webhook")
    analysis = {
        "gap_summary": {"open_count": 2, "up_count": 1, "down_count": 1},
        "nearest_open_gap": {
            "direction": "up",
            "fill_status": "partial",
            "zone_low": 101.0,
            "zone_high": 104.5,
            "gap_date": datetime(2026, 5, 1),
            "distance_from_current_pct": 2.31,
        },
    }

    embed = notifier.create_gap_focus_embed(
        ticker="SPY",
        analysis=analysis,
        is_positive=True,
    )

    assert "ניתוח גאפים" in embed["title"]
    field_names = [field["name"] for field in embed["fields"]]
    assert field_names == ["מצב גאפים", "גאפ קרוב"]
