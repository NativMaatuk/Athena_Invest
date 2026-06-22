from __future__ import annotations

import asyncio
import logging

from .market_snapshot import MarketSnapshotService

logger = logging.getLogger(__name__)


class MarketSnapshotScheduler:
    def __init__(self, service: MarketSnapshotService, interval_seconds: int):
        self._service = service
        self._interval_seconds = max(60, int(interval_seconds))
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop(), name="market-snapshot-refresh")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task:
            try:
                await self._task
            finally:
                self._task = None

    async def _run_loop(self) -> None:
        # Pre-warm cache immediately on startup for faster first paint.
        await self._run_once()
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._interval_seconds)
                break
            except asyncio.TimeoutError:
                await self._run_once()

    async def _run_once(self) -> None:
        try:
            await self._service.refresh_snapshot()
            logger.info("market snapshot refreshed in background")
        except Exception:
            logger.exception("market snapshot background refresh failed")
