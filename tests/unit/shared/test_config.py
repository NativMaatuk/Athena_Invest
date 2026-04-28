import pytest

from src.shared.config import Settings
from src.shared.errors import ValidationError


def test_settings_from_env_reads_defaults(base_settings_env):
    settings = Settings.from_env()
    assert settings.discord_bot_token == "dummy-token"
    assert settings.analysis_max_concurrent == 3
    assert settings.request_timeout_seconds == 15
    assert settings.enable_fear_greed_scheduler is True


def test_validate_for_bot_requires_token(clean_settings_env):
    # Override any .env values loaded by python-dotenv.
    from os import environ

    environ["DISCORD_BOT_TOKEN"] = ""
    settings = Settings.from_env()
    with pytest.raises(ValidationError, match="DISCORD_BOT_TOKEN is required"):
        settings.validate_for_bot()


def test_validate_for_fear_greed_requires_webhook(base_settings_env):
    from os import environ

    environ["WEBHOOK_URL"] = ""
    environ["WEBHOOK_FEAR_AND_GREED"] = ""
    settings = Settings.from_env()
    with pytest.raises(ValidationError, match="WEBHOOK_FEAR_AND_GREED or WEBHOOK_URL"):
        settings.validate_for_fear_greed()
