import asyncio

from src.domain.fear_greed_service import FearGreedService
from src.shared.logging import get_logger


logger = get_logger(__name__)


class FearGreedScheduler:
    """Background scheduler isolated from interactive ticker requests."""

    def __init__(self, service: FearGreedService, webhook_url: str, interval_minutes: int):
        self._service = service
        self._webhook_url = webhook_url
        self._interval_minutes = interval_minutes
        self._task: asyncio.Task | None = None

    async def _run_loop(self):
        while True:
            ok = await asyncio.to_thread(self._service.publish_once, self._webhook_url)
            if ok:
                logger.info("fear_greed_publish_success")
            else:
                logger.error("fear_greed_publish_failed")
            await asyncio.sleep(max(60, self._interval_minutes * 60))

    def start(self):
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run_loop())

    def stop(self):
        if self._task and not self._task.done():
            self._task.cancel()
