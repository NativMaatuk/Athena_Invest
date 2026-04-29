from src.presentation.error_messages import build_analysis_error_message
from src.shared.errors import TickerNotFoundError


def test_ticker_not_found_message_is_clear_and_formal():
    message = build_analysis_error_message("ZZZZ", TickerNotFoundError("missing"))
    assert "לא נמצא טיקר" in message
    assert "ZZZZ" in message


def test_generic_message_hides_internal_error():
    message = build_analysis_error_message("AAPL", RuntimeError("internal stacktrace"))
    assert "לא ניתן להשלים את הניתוח כרגע" in message
    assert "stacktrace" not in message
