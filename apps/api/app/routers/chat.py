from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..dependencies import enforce_rate_limit, get_perplexity_client, get_settings
from ..schemas import PerplexityChatRequest, PerplexityChatResponse
from ..services.perplexity_client import PerplexityClient

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("/perplexity", response_model=PerplexityChatResponse)
async def perplexity_chat(
    payload: PerplexityChatRequest,
    request: Request,
    client: PerplexityClient = Depends(get_perplexity_client),
) -> PerplexityChatResponse:
    settings = get_settings()
    enforce_rate_limit(
        request,
        bucket="chat",
        limit=settings.rate_limit_chat_requests,
    )
    try:
        answer, citations, model_name = await client.ask(
            api_key=payload.api_key,
            question=payload.question,
            model=payload.model,
            ticker_context=payload.ticker_context,
        )
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        if status_code in {401, 403}:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="מפתח ה-API של Perplexity לא תקין או חסום.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="שירות Perplexity לא זמין כרגע. נסה שוב מאוחר יותר.",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="נכשלה תקשורת עם שירות Perplexity.",
        ) from exc

    return PerplexityChatResponse(model=model_name, answer=answer, citations=citations)
