from __future__ import annotations

import logging

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from src.shared.errors import ExternalServiceError, RequestTimeoutError, TickerNotFoundError, ValidationError

logger = logging.getLogger("athena.web.api")


def _build_error_payload(
    request: Request,
    *,
    code: str,
    user_message: str,
    admin_message: str | None = None,
) -> dict:
    request_id = getattr(request.state, "request_id", "unknown")
    payload = {
        "error": {
            "code": code,
            "message": user_message,
            "request_id": request_id,
        }
    }
    if admin_message:
        payload["error"]["admin_message"] = admin_message
    return payload


async def ticker_not_found_handler(request: Request, exc: TickerNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=_build_error_payload(
            request,
            code="TICKER_NOT_FOUND",
            user_message="לא נמצא טיקר תואם. בדוק את הסימול ונסה שוב.",
            admin_message=str(exc),
        ),
    )


async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=_build_error_payload(
            request,
            code="VALIDATION_ERROR",
            user_message="הקלט שהוזן אינו תקין. בדוק את הטיקר ונסה שוב.",
            admin_message=str(exc),
        ),
    )


async def timeout_error_handler(request: Request, exc: RequestTimeoutError) -> JSONResponse:
    return JSONResponse(
        status_code=504,
        content=_build_error_payload(
            request,
            code="UPSTREAM_TIMEOUT",
            user_message="הניתוח התעכב מעבר לזמן הצפוי. נסה שוב בעוד רגע.",
            admin_message=str(exc),
        ),
    )


async def external_error_handler(request: Request, exc: ExternalServiceError) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content=_build_error_payload(
            request,
            code="UPSTREAM_ERROR",
            user_message="יש תקלה זמנית בשירות חיצוני. נסה שוב בעוד מספר דקות.",
            admin_message=str(exc),
        ),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    message = str(exc.detail) if exc.detail else "הבקשה נכשלה."
    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_payload(
            request,
            code=f"HTTP_{exc.status_code}",
            user_message=message,
            admin_message=message,
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception("unhandled_exception request_id=%s", request_id)
    return JSONResponse(
        status_code=500,
        content=_build_error_payload(
            request,
            code="UNEXPECTED_ERROR",
            user_message="אירעה תקלה לא צפויה. נסה שוב מאוחר יותר.",
            admin_message=str(exc),
        ),
    )
