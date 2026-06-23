from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

US_EASTERN = ZoneInfo("America/New_York")


def is_us_market_hours(now_utc: datetime | None = None) -> bool:
    current = now_utc or datetime.now(timezone.utc)
    current_et = current.astimezone(US_EASTERN)
    # Monday=0 ... Sunday=6
    if current_et.weekday() >= 5:
        return False
    minutes_since_midnight = current_et.hour * 60 + current_et.minute
    market_open = 9 * 60 + 30
    market_close = 16 * 60
    return market_open <= minutes_since_midnight < market_close


def market_refresh_interval_seconds(
    *,
    market_hours_seconds: int,
    off_hours_seconds: int,
    now_utc: datetime | None = None,
) -> int:
    if is_us_market_hours(now_utc):
        return max(30, int(market_hours_seconds))
    return max(30, int(off_hours_seconds))
