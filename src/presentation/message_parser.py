from src.domain.ticker_validation import normalize_ticker, validate_ticker
from src.shared.errors import ValidationError


def extract_ticker_from_message(content: str) -> str | None:
    """Return a validated ticker from free text, or None if message is not ticker-like."""
    if not content or " " in content.strip():
        return None

    ticker = normalize_ticker(content)
    if not ticker:
        return None

    try:
        validate_ticker(ticker)
    except ValidationError:
        return None
    return ticker
