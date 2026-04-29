from src.shared.errors import TickerNotFoundError


def build_analysis_error_message(ticker: str, error: Exception) -> str:
    """Return user-facing error text without leaking internal details."""
    if isinstance(error, TickerNotFoundError):
        return (
            f"❌ לא נמצא טיקר בשם **{ticker}**. "
            "נא לוודא שהסימול שהוזן נכון."
        )
    return "❌ לא ניתן להשלים את הניתוח כרגע. נסה שוב בעוד מספר דקות."
