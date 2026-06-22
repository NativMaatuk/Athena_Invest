from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class WatchlistStore:
    def __init__(self, db_path: str):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), timeout=15)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS watchlist_tickers (
                    ticker TEXT PRIMARY KEY,
                    added_at TEXT NOT NULL,
                    last_refreshed_at TEXT,
                    consecutive_failures INTEGER NOT NULL DEFAULT 0,
                    is_degraded INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT
                );

                CREATE TABLE IF NOT EXISTS watchlist_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    institutional_pct REAL,
                    insider_pct REAL,
                    volume_today REAL,
                    avg_volume_30d REAL,
                    relative_volume REAL,
                    top_holders_json TEXT NOT NULL DEFAULT '[]',
                    fetch_status TEXT NOT NULL DEFAULT 'ok',
                    error_message TEXT,
                    FOREIGN KEY(ticker) REFERENCES watchlist_tickers(ticker)
                );

                CREATE INDEX IF NOT EXISTS idx_watchlist_snapshots_ticker_time
                ON watchlist_snapshots(ticker, captured_at DESC);

                CREATE TABLE IF NOT EXISTS watchlist_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    holder_name TEXT,
                    change_pct REAL,
                    relative_volume REAL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_watchlist_events_created
                ON watchlist_events(created_at DESC);
                """
            )

    def list_tickers(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT ticker, added_at, last_refreshed_at, consecutive_failures, is_degraded, last_error
                FROM watchlist_tickers
                ORDER BY added_at ASC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def add_ticker(self, ticker: str, max_items: int) -> None:
        with self._lock, self._connect() as conn:
            count = conn.execute("SELECT COUNT(1) AS c FROM watchlist_tickers").fetchone()["c"]
            if count >= max_items:
                raise ValueError(f"ניתן לעקוב אחרי עד {max_items} מניות בלבד.")
            exists = conn.execute(
                "SELECT 1 FROM watchlist_tickers WHERE ticker = ?",
                (ticker,),
            ).fetchone()
            if exists:
                raise ValueError("המניה כבר קיימת ברשימת המעקב.")
            conn.execute(
                """
                INSERT INTO watchlist_tickers (ticker, added_at, last_refreshed_at, consecutive_failures, is_degraded)
                VALUES (?, ?, NULL, 0, 0)
                """,
                (ticker, utc_now_iso()),
            )

    def remove_ticker(self, ticker: str) -> bool:
        with self._lock, self._connect() as conn:
            deleted = conn.execute("DELETE FROM watchlist_tickers WHERE ticker = ?", (ticker,)).rowcount
            conn.execute("DELETE FROM watchlist_snapshots WHERE ticker = ?", (ticker,))
            conn.execute("DELETE FROM watchlist_events WHERE ticker = ?", (ticker,))
        return deleted > 0

    def latest_snapshot(self, ticker: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, ticker, captured_at, institutional_pct, insider_pct, volume_today,
                       avg_volume_30d, relative_volume, top_holders_json, fetch_status, error_message
                FROM watchlist_snapshots
                WHERE ticker = ?
                ORDER BY captured_at DESC
                LIMIT 1
                """,
                (ticker,),
            ).fetchone()
        if row is None:
            return None
        payload = dict(row)
        payload["top_holders"] = json.loads(payload.pop("top_holders_json") or "[]")
        return payload

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
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO watchlist_snapshots (
                    ticker, captured_at, institutional_pct, insider_pct, volume_today,
                    avg_volume_30d, relative_volume, top_holders_json, fetch_status, error_message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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

    def update_ticker_status(
        self,
        *,
        ticker: str,
        last_refreshed_at: str | None,
        consecutive_failures: int,
        is_degraded: bool,
        last_error: str | None,
    ) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE watchlist_tickers
                SET last_refreshed_at = ?,
                    consecutive_failures = ?,
                    is_degraded = ?,
                    last_error = ?
                WHERE ticker = ?
                """,
                (last_refreshed_at, consecutive_failures, 1 if is_degraded else 0, last_error, ticker),
            )

    def history(self, ticker: str, hours: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, ticker, captured_at, institutional_pct, insider_pct, volume_today,
                       avg_volume_30d, relative_volume, top_holders_json, fetch_status, error_message
                FROM watchlist_snapshots
                WHERE ticker = ?
                  AND captured_at >= datetime('now', ?)
                ORDER BY captured_at DESC
                """,
                (ticker, f"-{int(hours)} hours"),
            ).fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            payload = dict(row)
            payload["top_holders"] = json.loads(payload.pop("top_holders_json") or "[]")
            results.append(payload)
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
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO watchlist_events (
                    ticker, event_type, severity, message, holder_name, change_pct, relative_volume, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (ticker, event_type, severity, message, holder_name, change_pct, relative_volume, created_at),
            )

    def list_events(self, *, since_iso: str | None, limit: int) -> list[dict[str, Any]]:
        query = """
            SELECT id, ticker, event_type, severity, message, holder_name, change_pct, relative_volume, created_at
            FROM watchlist_events
        """
        params: list[Any] = []
        if since_iso:
            query += " WHERE created_at >= ?"
            params.append(since_iso)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(int(limit))
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(row) for row in rows]

    def latest_refresh_at(self) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT MAX(last_refreshed_at) AS latest FROM watchlist_tickers"
            ).fetchone()
        return row["latest"] if row and row["latest"] else None

    def prune_old_data(self, retention_days: int) -> None:
        days = max(1, int(retention_days))
        with self._lock, self._connect() as conn:
            conn.execute(
                "DELETE FROM watchlist_snapshots WHERE captured_at < datetime('now', ?)",
                (f"-{days} days",),
            )
            conn.execute(
                "DELETE FROM watchlist_events WHERE created_at < datetime('now', ?)",
                (f"-{days} days",),
            )
