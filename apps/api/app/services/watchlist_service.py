from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import yfinance as yf

from ..storage.watchlist_store import WatchlistStore, utc_now_iso


@dataclass
class RefreshSummary:
    refreshed: int
    failures: int
    events_created: int


class WatchlistService:
    def __init__(
        self,
        *,
        store: WatchlistStore,
        max_items: int,
        significant_change_pct: float,
        degraded_failure_threshold: int,
        retention_days: int,
    ):
        self._store = store
        self._max_items = max_items
        self._significant_change_pct = max(0.5, float(significant_change_pct))
        self._degraded_failure_threshold = max(1, int(degraded_failure_threshold))
        self._retention_days = max(1, int(retention_days))

    @property
    def max_items(self) -> int:
        return self._max_items

    def list_watchlist(self) -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        for item in self._store.list_tickers():
            latest = self._store.latest_snapshot(item["ticker"])
            items.append(
                {
                    "ticker": item["ticker"],
                    "added_at": item["added_at"],
                    "last_refreshed_at": item["last_refreshed_at"],
                    "is_degraded": bool(item["is_degraded"]),
                    "last_error": item["last_error"],
                    "latest_snapshot": latest,
                }
            )
        return {
            "max_items": self._max_items,
            "last_refresh_at": self._store.latest_refresh_at(),
            "items": items,
        }

    def add_ticker(self, ticker: str) -> dict[str, Any]:
        self._store.add_ticker(ticker, self._max_items)
        self.refresh_ticker(ticker)
        return self.list_watchlist()

    def remove_ticker(self, ticker: str) -> dict[str, Any]:
        removed = self._store.remove_ticker(ticker)
        if not removed:
            raise ValueError("הטיקר לא נמצא ברשימת המעקב.")
        return self.list_watchlist()

    def get_history(self, ticker: str, *, hours: int) -> list[dict[str, Any]]:
        return self._store.history(ticker, hours)

    def get_events(self, *, since_iso: str | None, limit: int) -> list[dict[str, Any]]:
        events = self._store.list_events(since_iso=since_iso, limit=limit)
        for event in events:
            event["anomaly_score"] = self._anomaly_score(
                event_type=str(event.get("event_type") or ""),
                change_pct=self._to_float(event.get("change_pct")),
                relative_volume=self._to_float(event.get("relative_volume")),
            )
        return events

    def refresh_watchlist(self) -> RefreshSummary:
        self._store.prune_old_data(self._retention_days)
        tickers = [item["ticker"] for item in self._store.list_tickers()]
        refreshed = 0
        failures = 0
        events_created = 0
        for ticker in tickers:
            try:
                events_created += self.refresh_ticker(ticker)
                refreshed += 1
            except Exception:
                failures += 1
        return RefreshSummary(refreshed=refreshed, failures=failures, events_created=events_created)

    def refresh_ticker(self, ticker: str) -> int:
        now_iso = utc_now_iso()
        previous_snapshot = self._store.latest_snapshot(ticker)
        try:
            snapshot = self._fetch_snapshot(ticker=ticker, captured_at=now_iso)
            self._store.insert_snapshot(ticker=ticker, **snapshot)
            self._store.update_ticker_status(
                ticker=ticker,
                last_refreshed_at=now_iso,
                consecutive_failures=0,
                is_degraded=False,
                last_error=None,
            )
            events = self._build_events(ticker=ticker, previous=previous_snapshot, current=snapshot)
            for event in events:
                self._store.insert_event(
                    ticker=ticker,
                    event_type=event["event_type"],
                    severity=event["severity"],
                    message=event["message"],
                    holder_name=event.get("holder_name"),
                    change_pct=event.get("change_pct"),
                    relative_volume=event.get("relative_volume"),
                    created_at=now_iso,
                )
            return len(events)
        except Exception as exc:
            current_failures = 1
            is_degraded = False
            if previous_snapshot:
                ticker_item = next((i for i in self._store.list_tickers() if i["ticker"] == ticker), None)
                if ticker_item:
                    current_failures = int(ticker_item.get("consecutive_failures", 0)) + 1
            if current_failures >= self._degraded_failure_threshold:
                is_degraded = True
            self._store.insert_snapshot(
                ticker=ticker,
                captured_at=now_iso,
                institutional_pct=None,
                insider_pct=None,
                volume_today=None,
                avg_volume_30d=None,
                relative_volume=None,
                top_holders=[],
                fetch_status="error",
                error_message=str(exc),
            )
            self._store.update_ticker_status(
                ticker=ticker,
                last_refreshed_at=now_iso,
                consecutive_failures=current_failures,
                is_degraded=is_degraded,
                last_error=str(exc),
            )
            raise

    def _fetch_snapshot(self, *, ticker: str, captured_at: str) -> dict[str, Any]:
        ticker_obj = yf.Ticker(ticker)
        info = ticker_obj.info or {}
        ownership = self._extract_ownership_data(ticker_obj=ticker_obj, info=info)
        volume_today, avg_volume_30d, relative_volume = self._extract_volume_metrics(ticker_obj=ticker_obj)
        return {
            "captured_at": captured_at,
            "institutional_pct": ownership.get("institutional_pct"),
            "insider_pct": ownership.get("insider_pct"),
            "volume_today": volume_today,
            "avg_volume_30d": avg_volume_30d,
            "relative_volume": relative_volume,
            "top_holders": ownership.get("top_holders", []),
            "fetch_status": "ok",
            "error_message": None,
        }

    def _extract_volume_metrics(self, *, ticker_obj: yf.Ticker) -> tuple[float | None, float | None, float | None]:
        frame = ticker_obj.history(period="3mo", interval="1d", auto_adjust=False)
        if frame is None or len(frame) == 0 or "Volume" not in frame.columns:
            return None, None, None
        volumes = pd.to_numeric(frame["Volume"], errors="coerce").dropna()
        if len(volumes) == 0:
            return None, None, None
        volume_today = float(volumes.iloc[-1])
        avg_volume_30d = float(volumes.tail(30).mean()) if len(volumes) >= 1 else None
        relative_volume: float | None = None
        if avg_volume_30d and avg_volume_30d > 0:
            relative_volume = volume_today / avg_volume_30d
        return volume_today, avg_volume_30d, relative_volume

    def _extract_ownership_data(self, *, ticker_obj: yf.Ticker, info: dict[str, Any]) -> dict[str, Any]:
        institutional_pct = self._normalize_ratio_to_pct(info.get("heldPercentInstitutions"))
        insider_pct = self._normalize_ratio_to_pct(info.get("heldPercentInsiders"))
        shares_outstanding = self._to_float(info.get("sharesOutstanding"))

        holders: list[dict[str, Any]] = []
        try:
            institutional_holders = ticker_obj.institutional_holders
            if isinstance(institutional_holders, pd.DataFrame) and not institutional_holders.empty:
                holders = self._normalize_holders(institutional_holders, shares_outstanding=shares_outstanding)
        except Exception:
            holders = []

        payload: dict[str, Any] = {"top_holders": holders}
        if institutional_pct is not None:
            payload["institutional_pct"] = institutional_pct
        if insider_pct is not None:
            payload["insider_pct"] = insider_pct
        return payload

    def _normalize_holders(
        self,
        holders_df: pd.DataFrame,
        *,
        shares_outstanding: float | None,
        max_holders: int = 5,
    ) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for _, row in holders_df.head(max_holders).iterrows():
            holder_name = row.get("Holder")
            if holder_name is None or str(holder_name).strip() == "":
                continue

            pct_raw = self._normalize_ratio_to_pct(row.get("% Out"))
            shares_count = self._to_float(row.get("Shares"))
            if pct_raw is None and shares_count and shares_outstanding and shares_outstanding > 0:
                pct_raw = (shares_count / shares_outstanding) * 100
            normalized.append(
                {
                    "name": str(holder_name),
                    "pct_out": pct_raw,
                    "pct_out_text": f"{pct_raw:.2f}%" if pct_raw is not None else None,
                    "shares": self._format_count(row.get("Shares")),
                    "value": self._format_count(row.get("Value")),
                }
            )
        return normalized

    @staticmethod
    def _format_count(value: Any) -> str | None:
        if value is None:
            return None
        try:
            numeric = float(value)
            if numeric >= 1_000_000_000_000:
                return f"{numeric / 1_000_000_000_000:.2f}T"
            if numeric >= 1_000_000_000:
                return f"{numeric / 1_000_000_000:.2f}B"
            if numeric >= 1_000_000:
                return f"{numeric / 1_000_000:.2f}M"
            if numeric >= 1_000:
                return f"{numeric / 1_000:.2f}K"
            return f"{numeric:.0f}"
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_ratio_to_pct(value: Any) -> float | None:
        if value is None:
            return None
        try:
            numeric = float(value)
            if numeric <= 0:
                return None
            if numeric <= 1:
                return numeric * 100
            return numeric
        except (TypeError, ValueError):
            return None

    def _build_events(
        self,
        *,
        ticker: str,
        previous: dict[str, Any] | None,
        current: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if not previous or previous.get("fetch_status") != "ok":
            return []

        events: list[dict[str, Any]] = []
        current_inst = self._to_float(current.get("institutional_pct"))
        previous_inst = self._to_float(previous.get("institutional_pct"))
        rel_volume = self._to_float(current.get("relative_volume"))
        threshold = self._significant_change_pct

        if current_inst is not None and previous_inst is not None:
            delta = current_inst - previous_inst
            if abs(delta) >= threshold:
                events.append(
                    {
                        "event_type": "institutional_pct_shift",
                        "severity": self._severity(abs(delta), rel_volume),
                        "message": (
                            f"{ticker}: אחוז המוסדיים השתנה ב-{abs(delta):.2f}% "
                            f"({previous_inst:.2f}% -> {current_inst:.2f}%)."
                        ),
                        "holder_name": None,
                        "change_pct": round(delta, 4),
                        "relative_volume": rel_volume,
                    }
                )

        previous_holders = self._holder_map(previous.get("top_holders"))
        current_holders = self._holder_map(current.get("top_holders"))
        all_holders = sorted(set(previous_holders) | set(current_holders))
        for holder_name in all_holders:
            prev_pct = previous_holders.get(holder_name)
            curr_pct = current_holders.get(holder_name)
            if prev_pct is None and curr_pct is not None:
                events.append(
                    {
                        "event_type": "holder_entered",
                        "severity": self._severity(curr_pct, rel_volume),
                        "message": f"{ticker}: {holder_name} נכנס/ה לרשימת המחזיקים המובילים ({curr_pct:.2f}%).",
                        "holder_name": holder_name,
                        "change_pct": round(curr_pct, 4),
                        "relative_volume": rel_volume,
                    }
                )
                continue
            if prev_pct is not None and curr_pct is None:
                events.append(
                    {
                        "event_type": "holder_exited",
                        "severity": self._severity(prev_pct, rel_volume),
                        "message": f"{ticker}: {holder_name} יצא/ה מרשימת המחזיקים המובילים.",
                        "holder_name": holder_name,
                        "change_pct": round(-prev_pct, 4),
                        "relative_volume": rel_volume,
                    }
                )
                continue
            if prev_pct is None or curr_pct is None:
                continue
            delta = curr_pct - prev_pct
            if abs(delta) >= threshold:
                direction = "holder_increased" if delta > 0 else "holder_reduced"
                verb = "הגדיל/ה" if delta > 0 else "הקטין/ה"
                events.append(
                    {
                        "event_type": direction,
                        "severity": self._severity(abs(delta), rel_volume),
                        "message": (
                            f"{ticker}: {holder_name} {verb} החזקה ב-{abs(delta):.2f}% "
                            f"({prev_pct:.2f}% -> {curr_pct:.2f}%)."
                        ),
                        "holder_name": holder_name,
                        "change_pct": round(delta, 4),
                        "relative_volume": rel_volume,
                    }
                )
        return events

    def _severity(self, change_pct_abs: float | None, relative_volume: float | None) -> str:
        change = change_pct_abs or 0.0
        rel = relative_volume or 0.0
        if change >= self._significant_change_pct * 2 or rel >= 3.0:
            return "high"
        if change >= self._significant_change_pct or rel >= 2.0:
            return "medium"
        return "low"

    def _anomaly_score(
        self,
        *,
        event_type: str,
        change_pct: float | None,
        relative_volume: float | None,
    ) -> int:
        score = 0.0
        abs_change = abs(change_pct or 0.0)
        rel_vol = max(0.0, relative_volume or 0.0)

        # Change component (0-60)
        change_ratio = min(1.0, abs_change / max(1.0, self._significant_change_pct * 2))
        score += change_ratio * 60

        # Volume confirmation component (0-25)
        volume_ratio = min(1.0, rel_vol / 3.0)
        score += volume_ratio * 25

        # Event-type impact component (0-15)
        type_bonus = {
            "holder_exited": 15,
            "holder_entered": 12,
            "institutional_pct_shift": 10,
            "holder_reduced": 8,
            "holder_increased": 8,
        }.get(event_type, 5)
        score += type_bonus

        return int(max(0, min(100, round(score))))

    @staticmethod
    def _holder_map(raw_holders: Any) -> dict[str, float]:
        if not isinstance(raw_holders, list):
            return {}
        payload: dict[str, float] = {}
        for holder in raw_holders:
            if not isinstance(holder, dict):
                continue
            name = holder.get("name")
            if not name:
                continue
            pct = WatchlistService._to_float(holder.get("pct_out"))
            if pct is None:
                pct_text = holder.get("pct_out_text")
                if isinstance(pct_text, str):
                    pct = WatchlistService._to_float(pct_text.replace("%", ""))
            if pct is None:
                continue
            payload[str(name)] = pct
        return payload

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def parse_since(since: str | None) -> str | None:
        if since is None:
            return None
        text = since.strip()
        if not text:
            return None
        normalized = text.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()
