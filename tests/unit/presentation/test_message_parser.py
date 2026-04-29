from src.presentation.message_parser import extract_ticker_from_message


def test_extract_ticker_from_single_token_message():
    assert extract_ticker_from_message("aapl") == "AAPL"
    assert extract_ticker_from_message(" brk.b ") == "BRK.B"


def test_extract_ticker_returns_none_for_sentences():
    assert extract_ticker_from_message("please analyze AAPL") is None
    assert extract_ticker_from_message("hello world") is None


def test_extract_ticker_returns_none_for_invalid_symbol():
    assert extract_ticker_from_message("A") is None
    assert extract_ticker_from_message("") is None
