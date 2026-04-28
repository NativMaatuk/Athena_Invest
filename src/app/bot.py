import asyncio
import time
import uuid
from dataclasses import dataclass

import discord
from discord.ext import commands, tasks

from agents.classic_analyzer import ClassicAnalyzer
from agents.discord_notifier import DiscordNotifier, FearAndGreedNotifier
from agents.ticker_info_agent import TickerInfoAgent
from src.app.request_guard import RequestGuard
from src.app.scheduler import FearGreedScheduler
from src.domain.analysis_service import AnalysisService
from src.domain.fear_greed_service import FearGreedService
from src.infrastructure.cache.cache_store import TTLCache
from src.infrastructure.clients.translation_client import TranslationTickerInfoClient
from src.infrastructure.clients.yfinance_client import YFinanceMarketDataClient
from src.infrastructure.discord.discord_publisher import DiscordPublisher
from src.presentation.error_messages import build_analysis_error_message
from src.presentation.message_parser import extract_ticker_from_message
from src.presentation.response_formatter import ResponseFormatter
from src.shared.config import Settings
from src.shared.logging import get_logger, setup_logging
from src.shared.metrics import MetricsCollector


logger = get_logger(__name__)


@dataclass
class AnalysisRequest:
    request_id: str
    ticker: str
    message: discord.Message
    status_message: discord.Message
    created_at: float


class BotApp:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.settings.validate_for_bot()

        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = commands.Bot(command_prefix="!", intents=intents)

        self._request_guard = RequestGuard(settings.user_cooldown_seconds)
        self._request_queue: asyncio.Queue[AnalysisRequest] = asyncio.Queue(
            maxsize=settings.request_queue_maxsize
        )
        self._worker_tasks: list[asyncio.Task] = []
        self._metrics = MetricsCollector()
        self._error_streak = 0
        self._scheduler: FearGreedScheduler | None = None

        analyzer = ClassicAnalyzer()
        ticker_agent = TickerInfoAgent()
        discord_notifier = DiscordNotifier(webhook_url=None)

        self._analysis_service = AnalysisService(
            market_data_client=YFinanceMarketDataClient(analyzer),
            ticker_info_client=TranslationTickerInfoClient(ticker_agent),
            formatter=ResponseFormatter(analyzer),
            request_timeout_seconds=settings.request_timeout_seconds,
            retry_attempts=settings.retry_attempts,
            analysis_cache=TTLCache(settings.analysis_cache_ttl_seconds),
            ticker_info_cache=TTLCache(settings.ticker_info_cache_ttl_seconds),
        )
        self._publisher = DiscordPublisher(discord_notifier)

        self._bind_events()

    def _bind_events(self) -> None:
        @self.bot.event
        async def on_ready():
            logger.info(f"bot_ready user={self.bot.user}")
            self._start_workers()
            if not self._heartbeat.is_running():
                self._heartbeat.start()
            self._start_scheduler_if_enabled()
            if self.settings.run_duration_hours:
                asyncio.create_task(self._shutdown_after_duration())

        @self.bot.event
        async def on_message(message: discord.Message):
            if message.author == self.bot.user:
                return
            if self.settings.discord_channel_id and str(message.channel.id) != str(
                self.settings.discord_channel_id
            ):
                return

            ticker = extract_ticker_from_message(message.content)
            if not ticker:
                await self.bot.process_commands(message)
                return

            allowed, remaining = self._request_guard.can_process(message.author.id)
            if not allowed:
                await message.channel.send(
                    f"⏱️ נא להמתין {remaining} שניות לפני בקשה נוספת."
                )
                return

            if self._request_queue.full():
                await message.channel.send(
                    "⚠️ המערכת כרגע בעומס גבוה. נסה שוב בעוד דקה."
                )
                return

            status_message = await self._publisher.send_processing(message.channel, ticker)
            request = AnalysisRequest(
                request_id=str(uuid.uuid4()),
                ticker=ticker,
                message=message,
                status_message=status_message,
                created_at=time.perf_counter(),
            )
            await self._request_queue.put(request)
            logger.info(
                f"analysis_queued request_id={request.request_id} ticker={ticker} queue_size={self._request_queue.qsize()}"
            )
            await self.bot.process_commands(message)

    def _start_workers(self) -> None:
        if self._worker_tasks:
            return
        for worker_idx in range(self.settings.analysis_max_concurrent):
            task = asyncio.create_task(self._worker_loop(worker_idx))
            self._worker_tasks.append(task)
        logger.info(f"workers_started count={len(self._worker_tasks)}")

    async def _worker_loop(self, worker_idx: int) -> None:
        while True:
            request = await self._request_queue.get()
            started = time.perf_counter()
            try:
                result = await self._analysis_service.analyze_ticker(request.ticker)
                await self._publisher.send_analysis(request.message.channel, result)
                await self._publisher.delete_status(request.status_message)

                latency_ms = (time.perf_counter() - request.created_at) * 1000
                self._metrics.record_success(latency_ms)
                self._error_streak = 0
                logger.info(
                    "analysis_success "
                    f"worker={worker_idx} request_id={request.request_id} ticker={request.ticker} latency_ms={latency_ms:.2f}"
                )
            except Exception as exc:  # noqa: BLE001
                latency_ms = (time.perf_counter() - started) * 1000
                self._metrics.record_error(latency_ms)
                self._error_streak += 1
                await self._publisher.update_status_error(
                    request.status_message,
                    build_analysis_error_message(request.ticker, exc),
                )
                logger.error(
                    "analysis_failed "
                    f"worker={worker_idx} request_id={request.request_id} ticker={request.ticker} "
                    f"error={exc} error_streak={self._error_streak}"
                )
            finally:
                self._request_queue.task_done()

    async def _shutdown_after_duration(self) -> None:
        hours = self.settings.run_duration_hours
        await asyncio.sleep(hours * 3600)
        logger.info(f"scheduled_shutdown hours={hours}")
        await self.bot.close()

    def _start_scheduler_if_enabled(self) -> None:
        if self._scheduler is not None:
            return
        if not self.settings.enable_fear_greed_scheduler:
            return

        webhook_url = self.settings.webhook_fear_and_greed or self.settings.webhook_url
        if not webhook_url:
            logger.warning("fear_greed_scheduler_disabled_missing_webhook")
            return

        service = FearGreedService(FearAndGreedNotifier())
        self._scheduler = FearGreedScheduler(
            service=service,
            webhook_url=webhook_url,
            interval_minutes=self.settings.fear_greed_interval_minutes,
        )
        self._scheduler.start()
        logger.info("fear_greed_scheduler_started")

    @tasks.loop(seconds=60)
    async def _heartbeat(self):
        snapshot = self._metrics.snapshot()
        try:
            with open(self.settings.heartbeat_file_path, "w", encoding="utf-8") as heartbeat_file:
                heartbeat_file.write(str(int(time.time())))
        except OSError as exc:
            logger.error(f"heartbeat_file_write_failed error={exc}")

        logger.info(
            "heartbeat "
            f"queue_size={self._request_queue.qsize()} "
            f"requests_total={snapshot['requests_total']} "
            f"success_total={snapshot['success_total']} "
            f"error_total={snapshot['error_total']} "
            f"p95_latency_ms={snapshot['p95_latency_ms']}"
        )
        if self._error_streak >= 5:
            logger.error(f"alert_consecutive_errors count={self._error_streak}")

    @_heartbeat.before_loop
    async def _wait_until_ready(self):
        await self.bot.wait_until_ready()
        self._heartbeat.change_interval(
            seconds=max(10, self.settings.heartbeat_interval_seconds)
        )

    def run(self) -> None:
        self.bot.run(self.settings.discord_bot_token)


def main() -> None:
    setup_logging()
    settings = Settings.from_env()
    app = BotApp(settings)
    app.run()


if __name__ == "__main__":
    main()
