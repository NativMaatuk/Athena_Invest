from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "athena-web-api"


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


class ChartDataResponse(BaseModel):
    ticker: str
    points: list[ChartPoint]


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
