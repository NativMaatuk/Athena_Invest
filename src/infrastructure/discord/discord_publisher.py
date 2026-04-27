import discord
import asyncio

from agents.discord_notifier import DiscordNotifier


class DiscordPublisher:
    """Sends analysis messages to Discord channels."""

    def __init__(self, formatter: DiscordNotifier):
        self._formatter = formatter

    async def send_processing(self, channel: discord.abc.Messageable, ticker: str):
        return await channel.send(f"⏳ מנתח את **{ticker}**... אנא המתן.")

    async def send_analysis(self, channel: discord.abc.Messageable, result) -> None:
        info = result.info or {}
        analysis = result.analysis or {}

        embed_data = self._formatter.create_analysis_embed(
            ticker=result.ticker,
            content=result.output_text,
            is_positive=analysis.get("is_positive", False),
            sector=info.get("sector"),
            industry=info.get("industry"),
            summary=info.get("summary"),
            market_cap=info.get("market_cap"),
            earnings_info=None,
        )

        file = None
        image_buffer = await asyncio.to_thread(
            self._formatter.generate_chart_image,
            result.df,
            result.ticker,
            analysis.get("is_positive", False),
        )
        if image_buffer:
            image_buffer.seek(0)
            file = discord.File(image_buffer, filename="chart.png")
            embed_data["image"] = {"url": "attachment://chart.png"}

        embed = discord.Embed.from_dict(embed_data)
        if file:
            await channel.send(embed=embed, file=file)
            return
        await channel.send(embed=embed)

    async def update_status_error(self, status_message: discord.Message, content: str) -> None:
        await status_message.edit(content=content)

    async def delete_status(self, status_message: discord.Message) -> None:
        await status_message.delete()
