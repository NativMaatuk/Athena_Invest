import io
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.infrastructure.discord.discord_publisher import AnalysisModeView, DiscordPublisher


class FakeNotifier:
    def __init__(self, image_buffer=None, chart_delay_seconds=0.0):
        self.image_buffer = image_buffer
        self.chart_delay_seconds = chart_delay_seconds
        self.embed_calls = 0
        self.last_chart_analysis = None
        self.last_chart_mode = None

    def create_analysis_embed(self, **kwargs):
        self.embed_calls += 1
        return {"title": "Test Analysis", "description": "ok"}

    def create_gap_focus_embed(self, **kwargs):
        return {"title": "Gap Focus", "description": "gaps"}

    def create_ownership_embed(self, **kwargs):
        return {"title": "Ownership", "description": "ownership"}

    def generate_chart_image(self, df, ticker, is_positive, analysis=None, chart_mode="full"):
        if self.chart_delay_seconds > 0:
            time.sleep(self.chart_delay_seconds)
        self.last_chart_analysis = analysis
        self.last_chart_mode = chart_mode
        return self.image_buffer


class MockInteractionResponse:
    def __init__(self):
        self.defer = AsyncMock()
        self.edit_message = AsyncMock()
        self._done = False

    def is_done(self):
        return self._done


class MockInteraction:
    def __init__(self):
        self.response = MockInteractionResponse()
        self.edit_original_response = AsyncMock()


def make_result():
    return SimpleNamespace(
        ticker="AAPL",
        output_text="analysis text",
        analysis={"is_positive": True},
        info={
            "sector": "Tech",
            "industry": "Software",
            "summary": "Summary",
            "market_cap": "$1T",
            "ownership": {"institutional_pct": 71.2},
        },
        df={"rows": [1]},
    )


def make_result_without_ownership():
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
    assert "view" in send_kwargs
    assert notifier.last_chart_analysis == make_result().analysis
    assert notifier.last_chart_mode == "full"
    view = send_kwargs["view"]
    labels = {item.label for item in view.children}
    assert "בעלות מוסדית" in labels


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
    assert "view" in send_kwargs
    assert notifier.last_chart_analysis == make_result().analysis
    assert notifier.last_chart_mode == "full"


@pytest.mark.asyncio
async def test_send_analysis_hides_ownership_button_without_data():
    notifier = FakeNotifier(image_buffer=None)
    publisher = DiscordPublisher(notifier)
    channel = AsyncMock()

    await publisher.send_analysis(channel, make_result_without_ownership())

    send_kwargs = channel.send.await_args.kwargs
    view = send_kwargs["view"]
    labels = {item.label for item in view.children}
    assert "בעלות מוסדית" not in labels


@pytest.mark.asyncio
async def test_gap_mode_uses_gap_focus_embed_payload():
    notifier = FakeNotifier(image_buffer=None)
    result = make_result()
    view = AnalysisModeView(notifier, result)

    embed, file = await view.build_message_payload("gaps_only")

    assert embed.title == "Gap Focus"
    assert file is None


@pytest.mark.asyncio
async def test_switch_mode_defers_then_edits_original_response():
    notifier = FakeNotifier(image_buffer=None)
    view = AnalysisModeView(notifier, make_result())
    interaction = MockInteraction()

    await view._show_ownership_mode(interaction)

    assert interaction.response.defer.await_count == 1
    assert interaction.edit_original_response.await_count == 1

    await view._switch_chart_mode(interaction, "full")

    assert interaction.response.defer.await_count == 2
    assert interaction.edit_original_response.await_count == 2


@pytest.mark.asyncio
async def test_switch_mode_handles_slow_chart_generation():
    notifier = FakeNotifier(image_buffer=None, chart_delay_seconds=0.05)
    view = AnalysisModeView(notifier, make_result())
    interaction = MockInteraction()

    await view._switch_chart_mode(interaction, "gaps_only")

    interaction.response.defer.assert_awaited_once()
    interaction.edit_original_response.assert_awaited_once()


@pytest.mark.asyncio
async def test_switch_mode_falls_back_to_response_edit_when_original_edit_fails():
    notifier = FakeNotifier(image_buffer=None)
    view = AnalysisModeView(notifier, make_result())
    interaction = MockInteraction()
    interaction.edit_original_response = AsyncMock(side_effect=RuntimeError("edit failed"))

    await view._switch_chart_mode(interaction, "gaps_only")

    interaction.response.defer.assert_awaited_once()
    interaction.response.edit_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_status_update_and_delete_paths():
    publisher = DiscordPublisher(FakeNotifier())
    status_message = AsyncMock()

    await publisher.update_status_error(status_message, "error")
    await publisher.delete_status(status_message)

    status_message.edit.assert_awaited_once_with(content="error")
    status_message.delete.assert_awaited_once()
