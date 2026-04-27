from agents.classic_analyzer import ClassicAnalyzer


class ResponseFormatter:
    """Formats analysis text using the classic analyzer style."""

    def __init__(self, analyzer: ClassicAnalyzer):
        self._analyzer = analyzer

    def format_analysis(self, ticker: str, analysis: dict) -> str:
        return self._analyzer.format_output(ticker, analysis)
