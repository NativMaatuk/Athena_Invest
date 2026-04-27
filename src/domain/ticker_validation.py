import re

from src.shared.errors import ValidationError


TICKER_PATTERN = re.compile(r"^[A-Z0-9.\-^]{2,12}$")


def normalize_ticker(raw_text: str) -> str:
    """Normalize user text into a ticker candidate."""
    content = (raw_text or "").strip().upper()
    ticker = "".join(c for c in content if c.isalnum() or c in {"-", ".", "^"})
    return ticker


def validate_ticker(ticker: str) -> None:
    if not ticker:
        raise ValidationError("Ticker is empty")
    if not TICKER_PATTERN.match(ticker):
        raise ValidationError("Ticker format is invalid")
