from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone

import requests
import yfinance as yf

from .market_hours import market_refresh_interval_seconds


def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class MarketSnapshot:
    updated_at_iso: str
    updated_at_local: str
    usd_ils: float | None
    usd_ils_change_pct: float | None
    fear_greed_score: float | None
    fear_greed_rating: str | None
    vix: float | None
    vix_change_pct: float | None
    spy_change_pct: float | None
    qqq_change_pct: float | None
    cache_ttl_seconds: int = 300


class MarketSnapshotService:
    _FEAR_GREED_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    _FEAR_GREED_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }
    def __init__(
        self,
        *,
        market_hours_ttl_seconds: int = 120,
        off_hours_ttl_seconds: int = 900,
    ):
        self._market_hours_ttl_seconds = max(30, int(market_hours_ttl_seconds))
        self._off_hours_ttl_seconds = max(30, int(off_hours_ttl_seconds))
        self._cached_snapshot: MarketSnapshot | None = None
        self._last_known_good_snapshot: MarketSnapshot | None = None
        self._cached_until: datetime = datetime.min.replace(tzinfo=timezone.utc)
        self._lock = asyncio.Lock()

    def refresh_interval_seconds(self, now: datetime | None = None) -> int:
        return market_refresh_interval_seconds(
            market_hours_seconds=self._market_hours_ttl_seconds,
            off_hours_seconds=self._off_hours_ttl_seconds,
            now_utc=now,
        )

    async def get_snapshot(self) -> MarketSnapshot:
        now = datetime.now(timezone.utc)
        if self._cached_snapshot and now < self._cached_until:
            return self._cached_snapshot

        async with self._lock:
            now = datetime.now(timezone.utc)
            if self._cached_snapshot and now < self._cached_until:
                return self._cached_snapshot

            snapshot = await asyncio.to_thread(self._build_snapshot)
            usable_snapshot = self._select_usable_snapshot(snapshot)
            ttl_seconds = self.refresh_interval_seconds(now)
            with_ttl = self._snapshot_with_cache_ttl(usable_snapshot, ttl_seconds=ttl_seconds)
            self._cached_snapshot = with_ttl
            self._cached_until = now + timedelta(seconds=ttl_seconds)
            return with_ttl

    async def refresh_snapshot(self) -> MarketSnapshot:
        async with self._lock:
            snapshot = await asyncio.to_thread(self._build_snapshot)
            now = datetime.now(timezone.utc)
            usable_snapshot = self._select_usable_snapshot(snapshot)
            ttl_seconds = self.refresh_interval_seconds(now)
            with_ttl = self._snapshot_with_cache_ttl(usable_snapshot, ttl_seconds=ttl_seconds)
            self._cached_snapshot = with_ttl
            self._cached_until = now + timedelta(seconds=ttl_seconds)
            return with_ttl

    def _build_snapshot(self) -> MarketSnapshot:
        usd_ils, usd_ils_change_pct = self._fetch_quote_with_change("USDILS=X")
        vix, vix_change_pct = self._fetch_quote_with_change("^VIX")
        _, spy_change_pct = self._fetch_quote_with_change("SPY")
        _, qqq_change_pct = self._fetch_quote_with_change("QQQ")
        fear_score, fear_rating = self._fetch_fear_greed()

        now = datetime.now(timezone.utc)
        return MarketSnapshot(
            updated_at_iso=now.isoformat(),
            updated_at_local=now.astimezone().strftime("%d.%m.%Y %H:%M"),
            usd_ils=usd_ils,
            usd_ils_change_pct=usd_ils_change_pct,
            fear_greed_score=fear_score,
            fear_greed_rating=fear_rating,
            vix=vix,
            vix_change_pct=vix_change_pct,
            spy_change_pct=spy_change_pct,
            qqq_change_pct=qqq_change_pct,
            cache_ttl_seconds=self.refresh_interval_seconds(now),
        )

    def _select_usable_snapshot(self, snapshot: MarketSnapshot) -> MarketSnapshot:
        if self._is_usable_snapshot(snapshot):
            self._last_known_good_snapshot = snapshot
            return snapshot
        if self._last_known_good_snapshot:
            return self._last_known_good_snapshot
        return snapshot

    @staticmethod
    def _snapshot_with_cache_ttl(snapshot: MarketSnapshot, *, ttl_seconds: int) -> MarketSnapshot:
        return replace(snapshot, cache_ttl_seconds=max(30, int(ttl_seconds)))

    @staticmethod
    def _is_usable_snapshot(snapshot: MarketSnapshot) -> bool:
        meaningful_values = (
            snapshot.usd_ils,
            snapshot.usd_ils_change_pct,
            snapshot.fear_greed_score,
            snapshot.vix,
            snapshot.vix_change_pct,
            snapshot.spy_change_pct,
            snapshot.qqq_change_pct,
        )
        return any(value is not None for value in meaningful_values)

    def _fetch_quote_with_change(self, symbol: str) -> tuple[float | None, float | None]:
        try:
            history = yf.Ticker(symbol).history(period="5d", interval="1d")
        except Exception:
            return None, None
        if history is None or history.empty or "Close" not in history:
            return None, None
        closes = history["Close"].dropna()
        if closes.empty:
            return None, None
        latest = _to_float(closes.iloc[-1])
        if latest is None:
            return None, None
        previous = _to_float(closes.iloc[-2]) if len(closes) >= 2 else latest
        if previous in (None, 0):
            return latest, None
        change_pct = ((latest - previous) / previous) * 100
        return latest, change_pct

    def _fetch_fear_greed(self) -> tuple[float | None, str | None]:
        try:
            response = requests.get(
                self._FEAR_GREED_URL,
                headers=self._FEAR_GREED_HEADERS,
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
            fg = payload.get("fear_and_greed", {})
            return _to_float(fg.get("score")), str(fg.get("rating")) if fg.get("rating") else None
        except Exception:
            return None, None
