from agents.fear_and_greed_agent import FearAndGreedAgent
from agents.discord_notifier import FearAndGreedNotifier


class FearGreedService:
    """Single-purpose service for fetching and publishing Fear & Greed updates."""

    def __init__(self, notifier: FearAndGreedNotifier):
        self._agent = FearAndGreedAgent()
        self._notifier = notifier

    def publish_once(self, webhook_url: str) -> bool:
        fng_data = self._agent.get_data()
        if not fng_data:
            return False
        return self._notifier.send_fear_and_greed(
            fng_data["score"],
            fng_data["rating"],
            fng_data["timestamp"],
            webhook_url=webhook_url,
        )
