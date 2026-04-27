from agents.classic_analyzer import ClassicAnalyzer


class YFinanceMarketDataClient:
    """Client wrapper around classic analyzer market data fetch."""

    def __init__(self, analyzer: ClassicAnalyzer):
        self._analyzer = analyzer

    def fetch_analysis_dataframe(self, ticker: str):
        return self._analyzer.analyze(ticker)

    def build_analysis(self, df, days_until_earnings, next_earnings_date):
        return self._analyzer.analyze_classic(df, days_until_earnings, next_earnings_date)
