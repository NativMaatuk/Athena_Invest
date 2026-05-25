from __future__ import annotations

import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.shared.errors import ExternalServiceError, RequestTimeoutError, TickerNotFoundError, ValidationError

from .dependencies import get_settings
from .error_handlers import (
    external_error_handler,
    http_exception_handler,
    ticker_not_found_handler,
    timeout_error_handler,
    unhandled_exception_handler,
    validation_error_handler,
)
from .routers.analysis import router as analysis_router
from .routers.chat import router as chat_router
from .routers.health import router as health_router
from .routers.market import router as market_router
from .routers.ticker import router as ticker_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Athena Invest Web API",
        version="0.1.0",
        description="Web API for ticker analysis, chart rendering and Perplexity chat.",
    )

    @app.middleware("http")
    async def attach_request_id(request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(TickerNotFoundError, ticker_not_found_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(RequestTimeoutError, timeout_error_handler)
    app.add_exception_handler(ExternalServiceError, external_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.include_router(health_router)
    app.include_router(market_router)
    app.include_router(analysis_router)
    app.include_router(ticker_router)
    app.include_router(chat_router)
    return app


app = create_app()
