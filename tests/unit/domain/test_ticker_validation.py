import pytest

from src.domain.ticker_validation import normalize_ticker, validate_ticker
from src.shared.errors import ValidationError


def test_normalize_ticker_uppercases_and_strips_symbols():
    assert normalize_ticker("  aapl  ") == "AAPL"
    assert normalize_ticker("msft!") == "MSFT"
    assert normalize_ticker("brk.b") == "BRK.B"


def test_validate_ticker_rejects_empty():
    with pytest.raises(ValidationError, match="Ticker is empty"):
        validate_ticker("")


def test_validate_ticker_rejects_invalid_format():
    with pytest.raises(ValidationError, match="Ticker format is invalid"):
        validate_ticker("A")


def test_validate_ticker_accepts_valid_symbols():
    validate_ticker("AAPL")
    validate_ticker("BRK.B")
    validate_ticker("BTC-USD")
