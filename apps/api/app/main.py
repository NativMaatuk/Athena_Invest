from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.shared.errors import ExternalServiceError, RequestTimeoutError, TickerNotFoundError, ValidationError

from .dependencies import (
    get_market_snapshot_scheduler,
    get_settings,
    get_watchlist_scheduler,
    get_watchlist_storage_backend,
)
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
from .routers.presence import router as presence_router
from .routers.ticker import router as ticker_router
from .routers.watchlist import router as watchlist_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    watchlist_backend = get_watchlist_storage_backend()
    logger.info(
        "starting athena web api",
        extra={
            "runtime_environment": settings.runtime_environment,
            "watchlist_storage_backend": watchlist_backend,
            "internal_schedulers_enabled": settings.enable_internal_schedulers,
        },
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if not settings.enable_internal_schedulers:
            yield
            return
        watchlist_scheduler = get_watchlist_scheduler()
        market_scheduler = get_market_snapshot_scheduler()
        watchlist_scheduler.start()
        market_scheduler.start()
        try:
            yield
        finally:
            await watchlist_scheduler.stop()
            await market_scheduler.stop()

    app = FastAPI(
        title="Athena Invest Web API",
        version="0.1.0",
        description="Web API for ticker analysis, chart rendering and Perplexity chat.",
        lifespan=lifespan,
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
    app.include_router(presence_router)
    app.include_router(analysis_router)
    app.include_router(ticker_router)
    app.include_router(chat_router)
    app.include_router(watchlist_router)
    return app


app = create_app()
