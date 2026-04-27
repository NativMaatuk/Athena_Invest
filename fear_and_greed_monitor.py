"""One-shot Fear & Greed publisher entrypoint."""

from agents.discord_notifier import FearAndGreedNotifier
from src.domain.fear_greed_service import FearGreedService
from src.shared.config import Settings
from src.shared.logging import get_logger, setup_logging


logger = get_logger(__name__)


def main() -> None:
    setup_logging()
    settings = Settings.from_env()
    settings.validate_for_fear_greed()

    webhook = settings.webhook_fear_and_greed or settings.webhook_url
    service = FearGreedService(FearAndGreedNotifier())
    success = service.publish_once(webhook_url=webhook)
    if success:
        logger.info("fear_greed_publish_success")
        return
    logger.error("fear_greed_publish_failed")


if __name__ == "__main__":
    main()
