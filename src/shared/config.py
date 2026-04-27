import os
from dataclasses import dataclass
from dotenv import load_dotenv

from .errors import ValidationError


def _to_bool(value: str, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    discord_bot_token: str
    discord_channel_id: str | None
    run_duration_hours: float | None
    analysis_max_concurrent: int
    request_queue_maxsize: int
    user_cooldown_seconds: int
    request_timeout_seconds: int
    retry_attempts: int
    analysis_cache_ttl_seconds: int
    ticker_info_cache_ttl_seconds: int
    heartbeat_interval_seconds: int
    heartbeat_file_path: str
    enable_fear_greed_scheduler: bool
    fear_greed_interval_minutes: int
    webhook_url: str | None
    webhook_fear_and_greed: str | None

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(
            discord_bot_token=os.getenv("DISCORD_BOT_TOKEN", ""),
            discord_channel_id=os.getenv("DISCORD_CHANNEL_ID"),
            run_duration_hours=(
                float(os.getenv("RUN_DURATION_HOURS"))
                if os.getenv("RUN_DURATION_HOURS")
                else None
            ),
            analysis_max_concurrent=int(os.getenv("ANALYSIS_MAX_CONCURRENT", "3")),
            request_queue_maxsize=int(os.getenv("REQUEST_QUEUE_MAXSIZE", "100")),
            user_cooldown_seconds=int(os.getenv("USER_COOLDOWN_SECONDS", "20")),
            request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "15")),
            retry_attempts=int(os.getenv("RETRY_ATTEMPTS", "1")),
            analysis_cache_ttl_seconds=int(os.getenv("ANALYSIS_CACHE_TTL_SECONDS", "180")),
            ticker_info_cache_ttl_seconds=int(os.getenv("TICKER_INFO_CACHE_TTL_SECONDS", "86400")),
            heartbeat_interval_seconds=int(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "60")),
            heartbeat_file_path=os.getenv("HEARTBEAT_FILE_PATH", "/tmp/athena_heartbeat"),
            enable_fear_greed_scheduler=_to_bool(
                os.getenv("ENABLE_FEAR_GREED_SCHEDULER"), True
            ),
            fear_greed_interval_minutes=int(os.getenv("FEAR_GREED_INTERVAL_MINUTES", "60")),
            webhook_url=os.getenv("WEBHOOK_URL"),
            webhook_fear_and_greed=os.getenv("WEBHOOK_FEAR_AND_GREED"),
        )

    def validate_for_bot(self) -> None:
        if not self.discord_bot_token:
            raise ValidationError("DISCORD_BOT_TOKEN is required for bot runtime")
        if self.analysis_max_concurrent < 1:
            raise ValidationError("ANALYSIS_MAX_CONCURRENT must be >= 1")
        if self.request_queue_maxsize < 1:
            raise ValidationError("REQUEST_QUEUE_MAXSIZE must be >= 1")
        if self.request_timeout_seconds < 1:
            raise ValidationError("REQUEST_TIMEOUT_SECONDS must be >= 1")

    def validate_for_fear_greed(self) -> None:
        if not (self.webhook_fear_and_greed or self.webhook_url):
            raise ValidationError(
                "WEBHOOK_FEAR_AND_GREED or WEBHOOK_URL is required for Fear & Greed publish"
            )
