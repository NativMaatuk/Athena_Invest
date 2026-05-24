from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yfinance as yf

from src.domain.ticker_validation import normalize_ticker, validate_ticker
from src.shared.errors import ValidationError


@dataclass(frozen=True)
class TickerSuggestion:
    symbol: str
    name: str
    exchange: str
    currency: str
    summary: str
    score: float


class LightweightTickerResolver:
    """Lightweight resolver for web MVP if full resolver is unavailable."""

    def suggest(self, raw_ticker: str, max_candidates: int = 5) -> list[TickerSuggestion]:
        normalized = normalize_ticker(raw_ticker)
        try:
            validate_ticker(normalized)
        except ValidationError:
            return []

        records = self._lookup_records(normalized)
        suggestions: list[TickerSuggestion] = []
        seen: set[str] = set()
        for index, item in enumerate(records):
            symbol = str(item.get("symbol", "")).strip().upper()
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            name = str(item.get("longname") or item.get("shortname") or symbol).strip()
            exchange = str(item.get("exchange") or "N/A").strip()
            score = max(0.0, 100.0 - index)
            suggestions.append(
                TickerSuggestion(
                    symbol=symbol,
                    name=name,
                    exchange=exchange,
                    currency=str(item.get("currency") or "N/A").strip(),
                    summary="",
                    score=score,
                )
            )

        if not suggestions:
            suggestions.append(
                TickerSuggestion(
                    symbol=normalized,
                    name=normalized,
                    exchange="N/A",
                    currency="N/A",
                    summary="",
                    score=50.0,
                )
            )
        return suggestions[: max(1, max_candidates)]

    @staticmethod
    def _lookup_records(query: str) -> list[dict[str, Any]]:
        try:
            raw = yf.Lookup(query).get_all(count=20)  # type: ignore[attr-defined]
        except Exception:
            return []

        if isinstance(raw, list):
            return [item for item in raw if isinstance(item, dict)]
        if isinstance(raw, dict):
            quotes = raw.get("quotes") or []
            if isinstance(quotes, list):
                return [item for item in quotes if isinstance(item, dict)]
        if hasattr(raw, "to_dict"):
            try:
                rows = raw.to_dict("records")
            except Exception:
                rows = []
            if isinstance(rows, list):
                return [item for item in rows if isinstance(item, dict)]
        return []
