from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..dependencies import get_runtime
from ..schemas import SuggestionItem, SuggestionResponse
from ..services.analysis_runtime import AnalysisRuntime

router = APIRouter(prefix="/api/v1/ticker", tags=["ticker"])


@router.get("/suggest", response_model=SuggestionResponse)
async def suggest_tickers(
    q: str = Query(min_length=1, max_length=20),
    max_candidates: int = Query(default=5, ge=1, le=10),
    runtime: AnalysisRuntime = Depends(get_runtime),
) -> SuggestionResponse:
    suggestions = runtime.ticker_resolver.suggest(q, max_candidates=max_candidates)
    return SuggestionResponse(
        query=q,
        suggestions=[
            SuggestionItem(
                symbol=item.symbol,
                name=item.name,
                exchange=item.exchange,
                currency=item.currency,
                summary=item.summary,
                score=item.score,
            )
            for item in suggestions
        ],
    )
