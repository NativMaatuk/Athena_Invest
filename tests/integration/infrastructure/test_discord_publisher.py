import io
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.infrastructure.discord.discord_publisher import DiscordPublisher


class FakeNotifier:
    def __init__(self, image_buffer=None):
        self.image_buffer = image_buffer
        self.embed_calls = 0

    def create_analysis_embed(self, **kwargs):
        self.embed_calls += 1
        return {"title": "Test Analysis", "description": "ok"}

    def generate_chart_image(self, df, ticker, is_positive):
        return self.image_buffer


def make_result():
    return SimpleNamespace(
        ticker="AAPL",
        output_text="analysis text",
        analysis={"is_positive": True},
        info={"sector": "Tech", "industry": "Software", "summary": "Summary", "market_cap": "$1T"},
        df={"rows": [1]},
    )


@pytest.mark.asyncio
async def test_send_analysis_without_chart_uses_embed_only():
    notifier = FakeNotifier(image_buffer=None)
    publisher = DiscordPublisher(notifier)
    channel = AsyncMock()

    await publisher.send_analysis(channel, make_result())

    channel.send.assert_awaited_once()
    send_kwargs = channel.send.await_args.kwargs
    assert "embed" in send_kwargs
    assert "file" not in send_kwargs


@pytest.mark.asyncio
async def test_send_analysis_with_chart_attaches_file():
    notifier = FakeNotifier(image_buffer=io.BytesIO(b"png-bytes"))
    publisher = DiscordPublisher(notifier)
    channel = AsyncMock()

    await publisher.send_analysis(channel, make_result())

    channel.send.assert_awaited_once()
    send_kwargs = channel.send.await_args.kwargs
    assert "embed" in send_kwargs
    assert "file" in send_kwargs


@pytest.mark.asyncio
async def test_status_update_and_delete_paths():
    publisher = DiscordPublisher(FakeNotifier())
    status_message = AsyncMock()

    await publisher.update_status_error(status_message, "error")
    await publisher.delete_status(status_message)

    status_message.edit.assert_awaited_once_with(content="error")
    status_message.delete.assert_awaited_once()
