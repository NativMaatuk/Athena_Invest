from agents.ticker_info_agent import TickerInfoAgent


class TranslationTickerInfoClient:
    """Client wrapper around translated ticker info retrieval."""

    def __init__(self, ticker_info_agent: TickerInfoAgent):
        self._ticker_info_agent = ticker_info_agent

    def get_ticker_info(self, ticker: str) -> dict:
        return self._ticker_info_agent.get_ticker_info(ticker)
