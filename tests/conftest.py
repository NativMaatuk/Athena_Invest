import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def clean_settings_env(monkeypatch):
    keys = [
        "DISCORD_BOT_TOKEN",
        "DISCORD_CHANNEL_ID",
        "RUN_DURATION_HOURS",
        "ANALYSIS_MAX_CONCURRENT",
        "REQUEST_QUEUE_MAXSIZE",
        "USER_COOLDOWN_SECONDS",
        "REQUEST_TIMEOUT_SECONDS",
        "RETRY_ATTEMPTS",
        "ANALYSIS_CACHE_TTL_SECONDS",
        "TICKER_INFO_CACHE_TTL_SECONDS",
        "HEARTBEAT_INTERVAL_SECONDS",
        "HEARTBEAT_FILE_PATH",
        "ENABLE_FEAR_GREED_SCHEDULER",
        "FEAR_GREED_INTERVAL_MINUTES",
        "WEBHOOK_URL",
        "WEBHOOK_FEAR_AND_GREED",
    ]
    for key in keys:
        monkeypatch.delenv(key, raising=False)
    yield


@pytest.fixture
def base_settings_env(clean_settings_env, monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "dummy-token")
    monkeypatch.setenv("DISCORD_CHANNEL_ID", "123")
    monkeypatch.setenv("ANALYSIS_MAX_CONCURRENT", "3")
    monkeypatch.setenv("REQUEST_QUEUE_MAXSIZE", "100")
    monkeypatch.setenv("USER_COOLDOWN_SECONDS", "20")
    monkeypatch.setenv("REQUEST_TIMEOUT_SECONDS", "15")
    monkeypatch.setenv("RETRY_ATTEMPTS", "1")
    monkeypatch.setenv("ANALYSIS_CACHE_TTL_SECONDS", "180")
    monkeypatch.setenv("TICKER_INFO_CACHE_TTL_SECONDS", "86400")
    monkeypatch.setenv("HEARTBEAT_INTERVAL_SECONDS", "60")
    monkeypatch.setenv("HEARTBEAT_FILE_PATH", os.devnull)
    monkeypatch.setenv("ENABLE_FEAR_GREED_SCHEDULER", "true")
    monkeypatch.setenv("FEAR_GREED_INTERVAL_MINUTES", "60")
    return monkeypatch
