from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "athena-web-api"
    watchlist_storage_backend: str = "unknown"
    internal_schedulers_enabled: bool = True


class SuggestionItem(BaseModel):
    symbol: str
    name: str
    exchange: str
    currency: str
    summary: str
    score: float


class SuggestionResponse(BaseModel):
    query: str
    suggestions: list[SuggestionItem]


class AnalysisRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)


class CompanyProfile(BaseModel):
    sector: str | None = None
    industry: str | None = None
    summary: str | None = None
    market_cap: str | None = None


class AnalysisPayload(BaseModel):
    ticker: str
    formatted_text_he: str
    is_positive: bool
    daily_change_pct: float | None = None
    technical_signal: str | None = None
    status: str | None = None
    risk: str | None = None
    gap_summary: dict
    nearest_open_gap: dict | None = None
    open_gaps: list[dict]
    ownership: dict | None = None
    company_profile: CompanyProfile
    analysis_raw: dict


class ChartPoint(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None
    sma_150: float | None = None
    bb_upper: float | None = None
    bb_middle: float | None = None
    bb_lower: float | None = None
    rsi: float | None = None


class ChartDataResponse(BaseModel):
    ticker: str
    points: list[ChartPoint]


class MarketSnapshotResponse(BaseModel):
    updated_at_iso: str
    updated_at_local: str
    usd_ils: float | None = None
    usd_ils_change_pct: float | None = None
    fear_greed_score: float | None = None
    fear_greed_rating: str | None = None
    vix: float | None = None
    vix_change_pct: float | None = None
    spy_change_pct: float | None = None
    qqq_change_pct: float | None = None
    cache_ttl_seconds: int = 300


class ActiveUsersHeartbeatRequest(BaseModel):
    session_id: str = Field(min_length=8, max_length=128)


class ActiveUsersResponse(BaseModel):
    active_users: int
    window_seconds: int


class PerplexityChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    api_key: str = Field(min_length=10, max_length=512)
    ticker_context: str | None = Field(default=None, max_length=20)
    model: str = Field(default="sonar-pro", max_length=64)


class PerplexityCitation(BaseModel):
    title: str | None = None
    url: str | None = None
    date: str | None = None


class PerplexityChatResponse(BaseModel):
    model: str
    answer: str
    citations: list[PerplexityCitation]


class WatchlistAddRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)


class WatchlistHolder(BaseModel):
    name: str
    pct_out: float | None = None
    pct_out_text: str | None = None
    shares: str | None = None
    value: str | None = None


class WatchlistSnapshot(BaseModel):
    id: int
    ticker: str
    captured_at: str
    institutional_pct: float | None = None
    insider_pct: float | None = None
    volume_today: float | None = None
    avg_volume_30d: float | None = None
    relative_volume: float | None = None
    top_holders: list[WatchlistHolder]
    fetch_status: str
    error_message: str | None = None


class WatchlistTickerItem(BaseModel):
    ticker: str
    added_at: str
    last_refreshed_at: str | None = None
    is_degraded: bool = False
    last_error: str | None = None
    latest_snapshot: WatchlistSnapshot | None = None


class WatchlistListResponse(BaseModel):
    max_items: int
    last_refresh_at: str | None = None
    items: list[WatchlistTickerItem]


class WatchlistHistoryResponse(BaseModel):
    ticker: str
    snapshots: list[WatchlistSnapshot]


class WatchlistEvent(BaseModel):
    id: int
    ticker: str
    event_type: str
    severity: str
    message: str
    holder_name: str | None = None
    change_pct: float | None = None
    relative_volume: float | None = None
    anomaly_score: int | None = None
    created_at: str


class WatchlistEventsResponse(BaseModel):
    events: list[WatchlistEvent]


class WatchlistRefreshResponse(BaseModel):
    refreshed: int
    failures: int
    events_created: int
