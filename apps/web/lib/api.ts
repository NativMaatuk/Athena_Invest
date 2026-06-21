export type SuggestionItem = {
  symbol: string;
  name: string;
  exchange: string;
  currency: string;
  summary: string;
  score: number;
};

export type AnalysisPayload = {
  ticker: string;
  formatted_text_he: string;
  is_positive: boolean;
  daily_change_pct?: number | null;
  technical_signal?: string | null;
  status?: string | null;
  risk?: string | null;
  gap_summary: Record<string, unknown>;
  nearest_open_gap?: Record<string, unknown> | null;
  open_gaps: Array<Record<string, unknown>>;
  ownership?: Record<string, unknown> | null;
  company_profile: {
    sector?: string | null;
    industry?: string | null;
    summary?: string | null;
    market_cap?: string | null;
  };
  analysis_raw: Record<string, unknown>;
};

export type ChatResponse = {
  model: string;
  answer: string;
  citations: Array<{ title?: string | null; url?: string | null; date?: string | null }>;
};

export type ChartPoint = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number | null;
  sma_150?: number | null;
  bb_upper?: number | null;
  bb_middle?: number | null;
  bb_lower?: number | null;
  rsi?: number | null;
};

export type MarketSnapshot = {
  updated_at_iso: string;
  updated_at_local: string;
  usd_ils?: number | null;
  usd_ils_change_pct?: number | null;
  fear_greed_score?: number | null;
  fear_greed_rating?: string | null;
  vix?: number | null;
  vix_change_pct?: number | null;
  spy_change_pct?: number | null;
  qqq_change_pct?: number | null;
  cache_ttl_seconds?: number;
};

export type ActiveUsersPayload = {
  active_users: number;
  window_seconds: number;
};

export type WatchlistHolder = {
  name: string;
  pct_out?: number | null;
  pct_out_text?: string | null;
  shares?: string | null;
  value?: string | null;
};

export type WatchlistSnapshot = {
  id: number;
  ticker: string;
  captured_at: string;
  institutional_pct?: number | null;
  insider_pct?: number | null;
  volume_today?: number | null;
  avg_volume_30d?: number | null;
  relative_volume?: number | null;
  top_holders: WatchlistHolder[];
  fetch_status: string;
  error_message?: string | null;
};

export type WatchlistTickerItem = {
  ticker: string;
  added_at: string;
  last_refreshed_at?: string | null;
  is_degraded: boolean;
  last_error?: string | null;
  latest_snapshot?: WatchlistSnapshot | null;
};

export type WatchlistListResponse = {
  max_items: number;
  last_refresh_at?: string | null;
  items: WatchlistTickerItem[];
};

export type WatchlistEvent = {
  id: number;
  ticker: string;
  event_type: string;
  severity: "low" | "medium" | "high";
  message: string;
  holder_name?: string | null;
  change_pct?: number | null;
  relative_volume?: number | null;
  anomaly_score?: number | null;
  created_at: string;
};

export type WatchlistHistoryResponse = {
  ticker: string;
  snapshots: WatchlistSnapshot[];
};

export type WatchlistEventsResponse = {
  events: WatchlistEvent[];
};

type ApiErrorEnvelope = {
  error?: {
    code?: string;
    message?: string;
    request_id?: string;
    admin_message?: string;
  };
};

export class ApiClientError extends Error {
  code: string;
  requestId?: string;
  adminMessage?: string;
  constructor(message: string, code: string, requestId?: string, adminMessage?: string) {
    super(message);
    this.name = "ApiClientError";
    this.code = code;
    this.requestId = requestId;
    this.adminMessage = adminMessage;
  }
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function parseOrThrow<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = "אירעה שגיאה בבקשה.";
    let code = `HTTP_${response.status}`;
    let requestId: string | undefined;
    let adminMessage: string | undefined;
    try {
      const payload = (await response.json()) as ApiErrorEnvelope;
      if (payload.error) {
        detail = payload.error.message ?? detail;
        code = payload.error.code ?? code;
        requestId = payload.error.request_id;
        adminMessage = payload.error.admin_message;
      }
    } catch {
      // keep default message
    }
    throw new ApiClientError(detail, code, requestId, adminMessage);
  }
  return (await response.json()) as T;
}

export async function fetchSuggestions(query: string): Promise<SuggestionItem[]> {
  if (!query.trim()) {
    return [];
  }
  const url = `${API_BASE}/api/v1/ticker/suggest?q=${encodeURIComponent(query.trim())}`;
  let response: Response;
  try {
    response = await fetch(url, { method: "GET", cache: "no-store" });
  } catch {
    throw new ApiClientError(
      "אין חיבור לשרת ה-API. ודא שה-API רץ על פורט 8000.",
      "NETWORK_ERROR",
    );
  }
  const payload = await parseOrThrow<{ suggestions: SuggestionItem[] }>(response);
  return payload.suggestions ?? [];
}

export async function fetchAnalysis(ticker: string): Promise<AnalysisPayload> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/v1/analysis`, {
      method: "POST",
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticker }),
    });
  } catch {
    throw new ApiClientError(
      "נכשלה תקשורת עם השרת. בדוק שה-API פעיל וזמין.",
      "NETWORK_ERROR",
    );
  }
  return parseOrThrow<AnalysisPayload>(response);
}

export function chartUrl(ticker: string, mode: "full" | "gaps_only"): string {
  return `${API_BASE}/api/v1/analysis/${encodeURIComponent(ticker)}/chart?mode=${mode}`;
}

export async function fetchChartData(ticker: string): Promise<ChartPoint[]> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/v1/analysis/${encodeURIComponent(ticker)}/chart-data`, {
      method: "GET",
      cache: "no-store",
    });
  } catch {
    throw new ApiClientError(
      "נכשלה תקשורת עם השרת בעת טעינת נתוני גרף.",
      "NETWORK_ERROR",
    );
  }
  const payload = await parseOrThrow<{ ticker: string; points: ChartPoint[] }>(response);
  return payload.points ?? [];
}

export async function fetchMarketSnapshot(): Promise<MarketSnapshot> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/v1/market/snapshot`, {
      method: "GET",
      cache: "no-store",
    });
  } catch {
    throw new ApiClientError(
      "לא ניתן לטעון נתוני שוק כרגע. בדוק שה-API פעיל.",
      "NETWORK_ERROR",
    );
  }
  return parseOrThrow<MarketSnapshot>(response);
}

export async function sendPresenceHeartbeat(sessionId: string): Promise<ActiveUsersPayload> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/v1/presence/heartbeat`, {
      method: "POST",
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
  } catch {
    throw new ApiClientError("לא ניתן לעדכן נוכחות כרגע.", "NETWORK_ERROR");
  }
  return parseOrThrow<ActiveUsersPayload>(response);
}

export async function fetchActiveUsers(): Promise<ActiveUsersPayload> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/v1/presence/active-users`, {
      method: "GET",
      cache: "no-store",
    });
  } catch {
    throw new ApiClientError("לא ניתן לטעון מספר משתמשים מחוברים כרגע.", "NETWORK_ERROR");
  }
  return parseOrThrow<ActiveUsersPayload>(response);
}

export async function askPerplexity(
  question: string,
  apiKey: string,
  tickerContext?: string,
): Promise<ChatResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/v1/chat/perplexity`, {
      method: "POST",
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        api_key: apiKey,
        ticker_context: tickerContext || null,
        model: "sonar-pro",
      }),
    });
  } catch {
    throw new ApiClientError(
      "לא ניתן להתחבר לשירות הצ'אט כרגע. ודא שה-API פעיל.",
      "NETWORK_ERROR",
    );
  }
  return parseOrThrow<ChatResponse>(response);
}

export async function fetchWatchlist(): Promise<WatchlistListResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/v1/watchlist`, {
      method: "GET",
      cache: "no-store",
    });
  } catch {
    throw new ApiClientError("לא ניתן לטעון את רשימת המעקב כרגע.", "NETWORK_ERROR");
  }
  return parseOrThrow<WatchlistListResponse>(response);
}

export async function addWatchlistTicker(ticker: string): Promise<WatchlistListResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/v1/watchlist`, {
      method: "POST",
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticker }),
    });
  } catch {
    throw new ApiClientError("לא ניתן להוסיף מניה לרשימת המעקב כרגע.", "NETWORK_ERROR");
  }
  return parseOrThrow<WatchlistListResponse>(response);
}

export async function removeWatchlistTicker(ticker: string): Promise<WatchlistListResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/v1/watchlist/${encodeURIComponent(ticker)}`, {
      method: "DELETE",
      cache: "no-store",
    });
  } catch {
    throw new ApiClientError("לא ניתן להסיר מניה מרשימת המעקב כרגע.", "NETWORK_ERROR");
  }
  return parseOrThrow<WatchlistListResponse>(response);
}

export async function fetchWatchlistHistory(ticker: string, hours = 168): Promise<WatchlistHistoryResponse> {
  let response: Response;
  try {
    response = await fetch(
      `${API_BASE}/api/v1/watchlist/${encodeURIComponent(ticker)}/history?hours=${encodeURIComponent(String(hours))}`,
      {
        method: "GET",
        cache: "no-store",
      },
    );
  } catch {
    throw new ApiClientError("לא ניתן לטעון היסטוריית אחזקות כרגע.", "NETWORK_ERROR");
  }
  return parseOrThrow<WatchlistHistoryResponse>(response);
}

export async function fetchWatchlistEvents(limit = 50): Promise<WatchlistEventsResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/v1/watchlist/events/feed?limit=${encodeURIComponent(String(limit))}`, {
      method: "GET",
      cache: "no-store",
    });
  } catch {
    throw new ApiClientError("לא ניתן לטעון אירועי מעקב כרגע.", "NETWORK_ERROR");
  }
  return parseOrThrow<WatchlistEventsResponse>(response);
}

export async function refreshWatchlist(): Promise<{ refreshed: number; failures: number; events_created: number }> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/v1/watchlist/refresh`, {
      method: "POST",
      cache: "no-store",
    });
  } catch {
    throw new ApiClientError("לא ניתן לרענן את רשימת המעקב כרגע.", "NETWORK_ERROR");
  }
  return parseOrThrow<{ refreshed: number; failures: number; events_created: number }>(response);
}
