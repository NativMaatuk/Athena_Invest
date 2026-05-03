import discord
import asyncio

from agents.discord_notifier import DiscordNotifier


class AnalysisModeView(discord.ui.View):
    """Interactive view to switch between full and gap-only charts."""

    def __init__(self, formatter: DiscordNotifier, result):
        super().__init__(timeout=900)
        self._formatter = formatter
        self._result = result
        self._current_mode = "full"
        self._has_ownership = bool((self._result.info or {}).get("ownership"))
        if not self._has_ownership:
            self.remove_item(self.show_ownership)
        self._sync_button_styles()

    async def build_message_payload(self, chart_mode: str):
        info = self._result.info or {}
        analysis = self._result.analysis or {}

        if chart_mode == "gaps_only":
            embed_data = self._formatter.create_gap_focus_embed(
                ticker=self._result.ticker,
                analysis=analysis,
                is_positive=analysis.get("is_positive", False),
            )
        else:
            embed_data = self._formatter.create_analysis_embed(
                ticker=self._result.ticker,
                content=self._result.output_text,
                is_positive=analysis.get("is_positive", False),
                sector=info.get("sector"),
                industry=info.get("industry"),
                summary=info.get("summary"),
                market_cap=info.get("market_cap"),
                earnings_info=None,
            )
            footer_text = embed_data.get("footer", {}).get("text", "Athena Invest Analysis")
            mode_text = "גרף מלא"
            embed_data["footer"] = {"text": f"{footer_text} | מצב: {mode_text}"}

        file = None
        image_buffer = await asyncio.to_thread(
            self._formatter.generate_chart_image,
            self._result.df,
            self._result.ticker,
            analysis.get("is_positive", False),
            analysis,
            chart_mode,
        )
        if image_buffer:
            image_buffer.seek(0)
            file = discord.File(image_buffer, filename="chart.png")
            embed_data["image"] = {"url": "attachment://chart.png"}

        embed = discord.Embed.from_dict(embed_data)
        return embed, file

    async def _switch_chart_mode(self, interaction: discord.Interaction, chart_mode: str) -> None:
        if chart_mode == self._current_mode:
            await interaction.response.defer()
            return

        self._current_mode = chart_mode
        self._sync_button_styles()
        embed, file = await self.build_message_payload(chart_mode)
        if file:
            await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
            return
        await interaction.response.edit_message(embed=embed, attachments=[], view=self)

    async def _show_ownership_mode(self, interaction: discord.Interaction) -> None:
        if not self._has_ownership:
            await interaction.response.defer()
            return
        self._current_mode = "ownership"
        self._sync_button_styles()
        info = self._result.info or {}
        analysis = self._result.analysis or {}
        embed_data = self._formatter.create_ownership_embed(
            ticker=self._result.ticker,
            ownership=info.get("ownership") or {},
            is_positive=analysis.get("is_positive", False),
        )
        embed = discord.Embed.from_dict(embed_data)
        await interaction.response.edit_message(embed=embed, attachments=[], view=self)

    def _sync_button_styles(self) -> None:
        self.show_full_chart.style = (
            discord.ButtonStyle.primary
            if self._current_mode == "full"
            else discord.ButtonStyle.secondary
        )
        self.show_gap_chart.style = (
            discord.ButtonStyle.primary
            if self._current_mode == "gaps_only"
            else discord.ButtonStyle.secondary
        )
        if self._has_ownership:
            self.show_ownership.style = (
                discord.ButtonStyle.primary
                if self._current_mode == "ownership"
                else discord.ButtonStyle.secondary
            )

    @discord.ui.button(label="גרף מלא", style=discord.ButtonStyle.primary, row=0)
    async def show_full_chart(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._switch_chart_mode(interaction, "full")

    @discord.ui.button(label="גאפים בלבד", style=discord.ButtonStyle.secondary, row=0)
    async def show_gap_chart(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._switch_chart_mode(interaction, "gaps_only")

    @discord.ui.button(label="בעלות מוסדית", style=discord.ButtonStyle.secondary, row=0)
    async def show_ownership(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_ownership_mode(interaction)


class DiscordPublisher:
    """Sends analysis messages to Discord channels."""

    def __init__(self, formatter: DiscordNotifier):
        self._formatter = formatter

    async def _send_quiet(self, channel: discord.abc.Messageable, **kwargs):
        """
        Send a message with strict mention suppression and best-effort silent delivery.
        Falls back if the installed discord.py version does not support `silent`.
        """
        safe_kwargs = {
            **kwargs,
            "allowed_mentions": discord.AllowedMentions.none(),
            "silent": True,
        }
        try:
            return await channel.send(**safe_kwargs)
        except TypeError:
            safe_kwargs.pop("silent", None)
            return await channel.send(**safe_kwargs)

    async def send_processing(self, channel: discord.abc.Messageable, ticker: str):
        return await self._send_quiet(channel, content=f"⏳ מנתח את **{ticker}**... אנא המתן.")

    async def send_analysis(self, channel: discord.abc.Messageable, result) -> None:
        view = AnalysisModeView(self._formatter, result)
        embed, file = await view.build_message_payload("full")
        if file:
            await self._send_quiet(channel, embed=embed, file=file, view=view)
            return
        await self._send_quiet(channel, embed=embed, view=view)

    async def update_status_error(self, status_message: discord.Message, content: str) -> None:
        await status_message.edit(content=content)

    async def delete_status(self, status_message: discord.Message) -> None:
        await status_message.delete()
