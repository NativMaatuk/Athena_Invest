from __future__ import annotations

import json
from datetime import datetime, timezone
from threading import Lock
from typing import Any


class PostgresWatchlistStore:
    def __init__(self, dsn: str):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ModuleNotFoundError as exc:  # pragma: no cover - environment-specific
            raise RuntimeError(
                "psycopg is required for PostgreSQL storage. Install apps/api/requirements.txt."
            ) from exc

        self._psycopg = psycopg
        self._dict_row = dict_row
        self._dsn = dsn
        self._lock = Lock()
        self._init_schema()

    def _connect(self):
        return self._psycopg.connect(self._dsn, row_factory=self._dict_row)

    @staticmethod
    def _to_iso(value: Any) -> Any:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()
        return value

    def _normalize_time_fields(self, payload: dict[str, Any], keys: list[str]) -> dict[str, Any]:
        for key in keys:
            if key in payload:
                payload[key] = self._to_iso(payload.get(key))
        return payload

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS watchlist_tickers (
                    ticker TEXT PRIMARY KEY,
                    added_at TIMESTAMPTZ NOT NULL,
                    last_refreshed_at TIMESTAMPTZ,
                    consecutive_failures INTEGER NOT NULL DEFAULT 0,
                    is_degraded BOOLEAN NOT NULL DEFAULT FALSE,
                    last_error TEXT
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS watchlist_snapshots (
                    id BIGSERIAL PRIMARY KEY,
                    ticker TEXT NOT NULL,
                    captured_at TIMESTAMPTZ NOT NULL,
                    institutional_pct DOUBLE PRECISION,
                    insider_pct DOUBLE PRECISION,
                    volume_today DOUBLE PRECISION,
                    avg_volume_30d DOUBLE PRECISION,
                    relative_volume DOUBLE PRECISION,
                    top_holders_json TEXT NOT NULL DEFAULT '[]',
                    fetch_status TEXT NOT NULL DEFAULT 'ok',
                    error_message TEXT
                );
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_watchlist_snapshots_ticker_time
                ON watchlist_snapshots(ticker, captured_at DESC);
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS watchlist_events (
                    id BIGSERIAL PRIMARY KEY,
                    ticker TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    holder_name TEXT,
                    change_pct DOUBLE PRECISION,
                    relative_volume DOUBLE PRECISION,
                    created_at TIMESTAMPTZ NOT NULL
                );
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_watchlist_events_created
                ON watchlist_events(created_at DESC);
                """
            )
            conn.commit()

    def list_tickers(self) -> list[dict[str, Any]]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT ticker, added_at, last_refreshed_at, consecutive_failures, is_degraded, last_error
                FROM watchlist_tickers
                ORDER BY added_at ASC
                """
            )
            rows = cur.fetchall()
        items: list[dict[str, Any]] = []
        for row in rows:
            payload = dict(row)
            items.append(self._normalize_time_fields(payload, ["added_at", "last_refreshed_at"]))
        return items

    def add_ticker(self, ticker: str, max_items: int) -> None:
        from .watchlist_store import utc_now_iso

        with self._lock, self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(1) AS c FROM watchlist_tickers")
            count = int(cur.fetchone()["c"])
            if count >= max_items:
                raise ValueError(f"ניתן לעקוב אחרי עד {max_items} מניות בלבד.")
            cur.execute("SELECT 1 FROM watchlist_tickers WHERE ticker = %s", (ticker,))
            if cur.fetchone():
                raise ValueError("המניה כבר קיימת ברשימת המעקב.")
            cur.execute(
                """
                INSERT INTO watchlist_tickers (ticker, added_at, last_refreshed_at, consecutive_failures, is_degraded)
                VALUES (%s, %s, NULL, 0, FALSE)
                """,
                (ticker, utc_now_iso()),
            )
            conn.commit()

    def remove_ticker(self, ticker: str) -> bool:
        with self._lock, self._connect() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM watchlist_tickers WHERE ticker = %s", (ticker,))
            deleted = cur.rowcount or 0
            cur.execute("DELETE FROM watchlist_snapshots WHERE ticker = %s", (ticker,))
            cur.execute("DELETE FROM watchlist_events WHERE ticker = %s", (ticker,))
            conn.commit()
        return deleted > 0

    def latest_snapshot(self, ticker: str) -> dict[str, Any] | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, ticker, captured_at, institutional_pct, insider_pct, volume_today,
                       avg_volume_30d, relative_volume, top_holders_json, fetch_status, error_message
                FROM watchlist_snapshots
                WHERE ticker = %s
                ORDER BY captured_at DESC
                LIMIT 1
                """,
                (ticker,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        payload = dict(row)
        payload["top_holders"] = json.loads(payload.pop("top_holders_json") or "[]")
        return self._normalize_time_fields(payload, ["captured_at"])

    def insert_snapshot(
        self,
        *,
        ticker: str,
        captured_at: str,
        institutional_pct: float | None,
        insider_pct: float | None,
        volume_today: float | None,
        avg_volume_30d: float | None,
        relative_volume: float | None,
        top_holders: list[dict[str, Any]],
        fetch_status: str = "ok",
        error_message: str | None = None,
    ) -> None:
        with self._lock, self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO watchlist_snapshots (
                    ticker, captured_at, institutional_pct, insider_pct, volume_today,
                    avg_volume_30d, relative_volume, top_holders_json, fetch_status, error_message
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    ticker,
                    captured_at,
                    institutional_pct,
                    insider_pct,
                    volume_today,
                    avg_volume_30d,
                    relative_volume,
                    json.dumps(top_holders, ensure_ascii=True),
                    fetch_status,
                    error_message,
                ),
            )
            conn.commit()

    def update_ticker_status(
        self,
        *,
        ticker: str,
        last_refreshed_at: str | None,
        consecutive_failures: int,
        is_degraded: bool,
        last_error: str | None,
    ) -> None:
        with self._lock, self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE watchlist_tickers
                SET last_refreshed_at = %s,
                    consecutive_failures = %s,
                    is_degraded = %s,
                    last_error = %s
                WHERE ticker = %s
                """,
                (last_refreshed_at, consecutive_failures, is_degraded, last_error, ticker),
            )
            conn.commit()

    def history(self, ticker: str, hours: int) -> list[dict[str, Any]]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, ticker, captured_at, institutional_pct, insider_pct, volume_today,
                       avg_volume_30d, relative_volume, top_holders_json, fetch_status, error_message
                FROM watchlist_snapshots
                WHERE ticker = %s
                  AND captured_at >= (NOW() - (%s * INTERVAL '1 hour'))
                ORDER BY captured_at DESC
                """,
                (ticker, int(hours)),
            )
            rows = cur.fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            payload = dict(row)
            payload["top_holders"] = json.loads(payload.pop("top_holders_json") or "[]")
            results.append(self._normalize_time_fields(payload, ["captured_at"]))
        return results

    def insert_event(
        self,
        *,
        ticker: str,
        event_type: str,
        severity: str,
        message: str,
        holder_name: str | None,
        change_pct: float | None,
        relative_volume: float | None,
        created_at: str,
    ) -> None:
        with self._lock, self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO watchlist_events (
                    ticker, event_type, severity, message, holder_name, change_pct, relative_volume, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (ticker, event_type, severity, message, holder_name, change_pct, relative_volume, created_at),
            )
            conn.commit()

    def list_events(self, *, since_iso: str | None, limit: int) -> list[dict[str, Any]]:
        with self._connect() as conn, conn.cursor() as cur:
            if since_iso:
                cur.execute(
                    """
                    SELECT id, ticker, event_type, severity, message, holder_name, change_pct, relative_volume, created_at
                    FROM watchlist_events
                    WHERE created_at >= %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (since_iso, int(limit)),
                )
            else:
                cur.execute(
                    """
                    SELECT id, ticker, event_type, severity, message, holder_name, change_pct, relative_volume, created_at
                    FROM watchlist_events
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (int(limit),),
                )
            rows = cur.fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            payload = dict(row)
            results.append(self._normalize_time_fields(payload, ["created_at"]))
        return results

    def latest_refresh_at(self) -> str | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT MAX(last_refreshed_at) AS latest FROM watchlist_tickers")
            row = cur.fetchone()
        if not row:
            return None
        return self._to_iso(row.get("latest"))

    def prune_old_data(self, retention_days: int) -> None:
        days = max(1, int(retention_days))
        with self._lock, self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM watchlist_snapshots WHERE captured_at < (NOW() - (%s * INTERVAL '1 day'))",
                (days,),
            )
            cur.execute(
                "DELETE FROM watchlist_events WHERE created_at < (NOW() - (%s * INTERVAL '1 day'))",
                (days,),
            )
            conn.commit()
