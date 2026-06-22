import pandas as pd

import agents.ticker_info_agent as ticker_info_module
from agents.ticker_info_agent import TickerInfoAgent


class FakeTranslator:
    def translate(self, text):
        return text


class FakeTickerWithOwnership:
    info = {
        "sector": "Technology",
        "industry": "Software",
        "longBusinessSummary": "Builds software products.",
        "marketCap": 2_500_000_000_000,
        "heldPercentInstitutions": 0.73,
        "heldPercentInsiders": 0.01,
    }
    institutional_holders = pd.DataFrame(
        [
            {"Holder": "Vanguard", "Shares": 100_000_000, "Value": 1_000_000_000, "% Out": 0.051},
            {"Holder": "BlackRock", "Shares": 90_000_000, "Value": 900_000_000, "% Out": 0.043},
        ]
    )


class FakeTickerWithoutOwnership:
    info = {
        "sector": "Technology",
        "industry": "Software",
        "longBusinessSummary": "Builds software products.",
        "marketCap": 2_500_000_000_000,
    }
    institutional_holders = pd.DataFrame()


class FakeTickerOwnershipPctFallback:
    info = {
        "sector": "Technology",
        "industry": "Software",
        "longBusinessSummary": "Builds software products.",
        "marketCap": 2_500_000_000_000,
        "heldPercentInstitutions": 0.73,
        "heldPercentInsiders": 0.01,
        "sharesOutstanding": 1_000_000_000,
    }
    institutional_holders = pd.DataFrame(
        [
            {"Holder": "Vanguard", "Shares": 60_000_000, "Value": 1_000_000_000, "% Out": None},
        ]
    )


def test_get_ticker_info_includes_ownership_when_available(monkeypatch):
    monkeypatch.setattr(ticker_info_module.yf, "Ticker", lambda _: FakeTickerWithOwnership())
    agent = TickerInfoAgent()
    agent.translator = FakeTranslator()

    info = agent.get_ticker_info("AAPL")

    assert "ownership" in info
    assert info["ownership"]["institutional_pct"] == 73.0
    assert info["ownership"]["insider_pct"] == 1.0
    assert len(info["ownership"]["top_holders"]) == 2


def test_get_ticker_info_hides_ownership_when_not_available(monkeypatch):
    monkeypatch.setattr(ticker_info_module.yf, "Ticker", lambda _: FakeTickerWithoutOwnership())
    agent = TickerInfoAgent()
    agent.translator = FakeTranslator()

    info = agent.get_ticker_info("AAPL")

    assert "ownership" not in info


def test_get_ticker_info_computes_holder_pct_when_out_missing(monkeypatch):
    monkeypatch.setattr(ticker_info_module.yf, "Ticker", lambda _: FakeTickerOwnershipPctFallback())
    agent = TickerInfoAgent()
    agent.translator = FakeTranslator()

    info = agent.get_ticker_info("AAPL")

    holder = info["ownership"]["top_holders"][0]
    assert holder["pct_out"] == "6.00%"
