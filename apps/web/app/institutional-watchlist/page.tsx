"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";

import {
  WatchlistEvent,
  WatchlistListResponse,
  WatchlistSnapshot,
  addWatchlistTicker,
  fetchWatchlist,
  fetchWatchlistEvents,
  fetchWatchlistHistory,
  refreshWatchlist,
  removeWatchlistTicker,
} from "@/lib/api";
import { InfoTooltip } from "@/app/components/info-tooltip";
import { MarketTopBar } from "@/app/components/market-top-bar";

function formatNumber(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) {
    return "—";
  }
  return Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(value);
}

function formatWatchlistTime(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString("he-IL");
}

function eventSeverityLabel(level: WatchlistEvent["severity"]): string {
  if (level === "high") {
    return "גבוה";
  }
  if (level === "medium") {
    return "בינוני";
  }
  return "נמוך";
}

function anomalyScoreTone(score: number | null | undefined): string {
  const value = score ?? 0;
  if (value >= 75) {
    return "border border-rose-500/40 bg-rose-950/20 text-rose-200";
  }
  if (value >= 45) {
    return "border border-amber-500/40 bg-amber-950/20 text-amber-200";
  }
  return "border border-slate-600 bg-slate-900 text-slate-200";
}

function freshnessLabel(value: string | null | undefined): { text: string; tone: "good" | "warn" | "bad" } {
  if (!value) {
    return { text: "אין עדכון", tone: "bad" };
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return { text: "לא ידוע", tone: "warn" };
  }
  const minutes = Math.max(0, Math.round((Date.now() - parsed.getTime()) / 60_000));
  if (minutes <= 70) {
    return { text: "עדכני", tone: "good" };
  }
  if (minutes <= 180) {
    return { text: `התעכב ${minutes} דק'`, tone: "warn" };
  }
  return { text: `ישן ${minutes} דק'`, tone: "bad" };
}

function metricTooltip(metric: string): string {
  const tips: Record<string, string> = {
    freshness: "מציג עד כמה נתוני המעקב עדכניים ביחס לרענון הרקע השעתי בשרת.",
    critical_events: "מספר אירועים בדרגת חומרה גבוהה, למשל שינוי מוסדי חד או שינוי עם נפח חריג.",
    degraded_count: "כמות מניות שהרענון שלהן נכשל מספר פעמים ברצף ודורשות בדיקה.",
    background_refresh: "הרענון השעתי מתבצע בצד השרת גם אם אף משתמש לא מחובר.",
    institutional_pct: "אחוז מהמניות של החברה שמוחזקות על ידי גופים מוסדיים.",
    insider_pct: "אחוז מהמניות של החברה שמוחזקות על ידי הנהלה ובעלי עניין.",
    rvol: "יחס בין נפח המסחר היומי לנפח הממוצע ב-30 הימים האחרונים.",
    volume_today: "סך המניות שנמסחרו ביום המסחר האחרון.",
    avg_volume_30d: "נפח ממוצע של 30 ימי מסחר אחרונים.",
    updated_at: "זמן העדכון האחרון שנשמר בשרת עבור המניה.",
    top_holders: "המחזיקים המוסדיים הבולטים. לכל מחזיק מוצגים כמות מניות ושווי החזקה.",
    anomaly_score:
      "ציון חריגות 0-100, מחושב משילוב של שינוי בהחזקה, Relative Volume וסוג האירוע. ציון גבוה אומר אירוע חריג יותר.",
  };
  return tips[metric] ?? "הסבר למטריקה זו.";
}

export default function InstitutionalWatchlistPage() {
  const [watchlist, setWatchlist] = useState<WatchlistListResponse | null>(null);
  const [watchlistEvents, setWatchlistEvents] = useState<WatchlistEvent[]>([]);
  const [watchlistTickerInput, setWatchlistTickerInput] = useState("");
  const [watchlistError, setWatchlistError] = useState<string | null>(null);
  const [isWatchlistBusy, setIsWatchlistBusy] = useState(false);
  const [isWatchlistRefreshing, setIsWatchlistRefreshing] = useState(false);
  const [selectedHistoryTicker, setSelectedHistoryTicker] = useState<string | null>(null);
  const [historySnapshots, setHistorySnapshots] = useState<WatchlistSnapshot[]>([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);

  async function loadWatchlistOverview() {
    try {
      const [listData, eventsData] = await Promise.all([fetchWatchlist(), fetchWatchlistEvents(50)]);
      setWatchlist(listData);
      setWatchlistEvents(eventsData.events ?? []);
      if (!selectedHistoryTicker && listData.items.length > 0) {
        setSelectedHistoryTicker(listData.items[0].ticker);
      }
      setWatchlistError(null);
    } catch (error) {
      const message = error instanceof Error ? error.message : "טעינת רשימת המעקב נכשלה.";
      setWatchlistError(message);
    }
  }

  useEffect(() => {
    void loadWatchlistOverview();
    const timer = window.setInterval(() => {
      void loadWatchlistOverview();
    }, 60_000);
    return () => {
      window.clearInterval(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedHistoryTicker) {
      setHistorySnapshots([]);
      return;
    }
    const ticker = selectedHistoryTicker;
    let active = true;
    async function loadHistory() {
      setIsHistoryLoading(true);
      try {
        const history = await fetchWatchlistHistory(ticker, 24 * 7);
        if (active) {
          setHistorySnapshots(history.snapshots ?? []);
        }
      } catch (error) {
        if (active) {
          const message = error instanceof Error ? error.message : "טעינת היסטוריה נכשלה.";
          setWatchlistError(message);
        }
      } finally {
        if (active) {
          setIsHistoryLoading(false);
        }
      }
    }
    void loadHistory();
    return () => {
      active = false;
    };
  }, [selectedHistoryTicker]);

  async function onAddWatchlistTicker(event: FormEvent) {
    event.preventDefault();
    if (!watchlistTickerInput.trim()) {
      return;
    }
    setIsWatchlistBusy(true);
    setWatchlistError(null);
    try {
      const next = await addWatchlistTicker(watchlistTickerInput.trim());
      setWatchlist(next);
      setWatchlistTickerInput("");
      await loadWatchlistOverview();
    } catch (error) {
      const message = error instanceof Error ? error.message : "הוספת מניה למעקב נכשלה.";
      setWatchlistError(message);
    } finally {
      setIsWatchlistBusy(false);
    }
  }

  async function onRemoveWatchlistTicker(ticker: string) {
    setIsWatchlistBusy(true);
    setWatchlistError(null);
    try {
      const next = await removeWatchlistTicker(ticker);
      setWatchlist(next);
      if (selectedHistoryTicker === ticker) {
        setSelectedHistoryTicker(next.items[0]?.ticker ?? null);
      }
      await loadWatchlistOverview();
    } catch (error) {
      const message = error instanceof Error ? error.message : "הסרת מניה מהמעקב נכשלה.";
      setWatchlistError(message);
    } finally {
      setIsWatchlistBusy(false);
    }
  }

  async function onManualWatchlistRefresh() {
    setIsWatchlistRefreshing(true);
    setWatchlistError(null);
    try {
      await refreshWatchlist();
      await loadWatchlistOverview();
    } catch (error) {
      const message = error instanceof Error ? error.message : "רענון ידני נכשל.";
      setWatchlistError(message);
    } finally {
      setIsWatchlistRefreshing(false);
    }
  }

  const watchlistItems = watchlist?.items ?? [];
  const highSeverityEvents = watchlistEvents.filter((event) => event.severity === "high").length;
  const degradedTickersCount = watchlistItems.filter((item) => item.is_degraded).length;
  const watchlistFreshness = freshnessLabel(watchlist?.last_refresh_at);

  return (
    <main className="mx-auto min-h-screen w-full max-w-none px-3 py-6 sm:px-5 md:px-8 md:py-8 athena-page">
      <MarketTopBar />
      <section className="mb-5 rounded-2xl border border-slate-700 bg-slate-900/70 p-4 shadow-lg sm:p-5 athena-card">
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl athena-title">מסך ניטור בעלות מוסדית</h1>
          <Link href="/" className="rounded-lg border border-slate-500 bg-slate-950 px-3 py-1 text-xs font-semibold text-slate-100 hover:border-violet-400 hover:text-violet-300">
            חזרה למסך הראשי
          </Link>
        </div>
      </section>

      <section className="mb-8 rounded-2xl border border-slate-700 bg-slate-900/70 p-4 sm:p-5 md:p-6 athena-card">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="rounded-lg border border-slate-600 bg-slate-950 px-3 py-2 text-xs text-slate-200 athena-subcard">
            מניות במעקב: <span className="font-semibold">{watchlistItems.length}</span>/
            <span className="font-semibold">{watchlist?.max_items ?? 5}</span> | רענון אחרון:{" "}
            <span className="ltr-number">{formatWatchlistTime(watchlist?.last_refresh_at)}</span>
          </div>
        </div>
        <div className="mb-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs athena-subcard">
            <p className="flex items-center gap-1 athena-muted">סטטוס עדכניות <InfoTooltip label="הסבר סטטוס עדכניות" content={metricTooltip("freshness")} /></p>
            <p className={`mt-1 font-semibold ${watchlistFreshness.tone === "good" ? "athena-positive" : watchlistFreshness.tone === "warn" ? "athena-warning" : "athena-negative"}`}>{watchlistFreshness.text}</p>
          </div>
          <div className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs athena-subcard">
            <p className="flex items-center gap-1 athena-muted">אירועים חמורים (24/7) <InfoTooltip label="הסבר אירועים חמורים" content={metricTooltip("critical_events")} /></p>
            <p className="mt-1 font-semibold athena-title">{highSeverityEvents}</p>
          </div>
          <div className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs athena-subcard">
            <p className="flex items-center gap-1 athena-muted">מניות במצב Degraded <InfoTooltip label="הסבר degraded" content={metricTooltip("degraded_count")} /></p>
            <p className={`mt-1 font-semibold ${degradedTickersCount > 0 ? "athena-warning" : "athena-positive"}`}>{degradedTickersCount}</p>
          </div>
          <div className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs athena-subcard">
            <p className="flex items-center gap-1 athena-muted">רענון רקע <InfoTooltip label="הסבר רענון רקע" content={metricTooltip("background_refresh")} /></p>
            <p className="mt-1 font-semibold athena-info">כל שעה אוטומטי בשרת</p>
          </div>
        </div>

        <form className="mb-4 flex flex-col gap-3 md:flex-row" onSubmit={onAddWatchlistTicker}>
          <input
            aria-label="הוסף מניה למעקב בעלות מוסדית"
            className="flex-1 rounded-lg border border-slate-500 bg-slate-950 px-3 py-2 text-slate-50 outline-none ring-cyan-400 transition focus:ring-2 athena-input"
            placeholder="לדוגמה: NVDA"
            value={watchlistTickerInput}
            onChange={(event) => setWatchlistTickerInput(event.target.value.toUpperCase())}
          />
          <button type="submit" disabled={isWatchlistBusy || !watchlistTickerInput.trim()} className="rounded-lg px-4 py-2 font-semibold disabled:cursor-not-allowed athena-primary-btn">
            {isWatchlistBusy ? "מעדכן..." : "הוסף למעקב"}
          </button>
          <button type="button" onClick={() => void onManualWatchlistRefresh()} disabled={isWatchlistRefreshing} className="rounded-lg border border-slate-500 bg-slate-950 px-4 py-2 text-sm font-semibold text-slate-100 hover:border-violet-400 hover:text-violet-300 disabled:cursor-not-allowed">
            {isWatchlistRefreshing ? "מרענן..." : "רענון ידני"}
          </button>
        </form>
        {watchlistError && <p className="mb-3 text-sm text-rose-300">{watchlistError}</p>}

        <div className="grid gap-5 lg:grid-cols-3">
          <div className="space-y-3 lg:col-span-2">
            {watchlistItems.length ? (
              watchlistItems.map((item) => {
                const isSelected = selectedHistoryTicker === item.ticker;
                return (
                  <article key={item.ticker} className={`rounded-xl border p-3 text-sm text-slate-100 athena-subcard ${item.is_degraded ? "border-amber-500/50 bg-amber-950/10" : "border-slate-700 bg-slate-950"}`}>
                    <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                      <button type="button" onClick={() => setSelectedHistoryTicker(item.ticker)} className={`rounded px-2 py-1 text-left text-base font-semibold ${isSelected ? "athena-tab-btn-active" : "athena-tab-btn"}`}>
                        {item.ticker} {isSelected ? "▾" : "▸"}
                      </button>
                      <div className="flex items-center gap-2">
                        {item.is_degraded && <span className="rounded-full border border-amber-500/40 bg-amber-900/30 px-2 py-1 text-xs text-amber-200">Degraded</span>}
                        <button type="button" onClick={() => void onRemoveWatchlistTicker(item.ticker)} className="rounded border border-rose-500/50 px-2 py-1 text-xs text-rose-200 hover:bg-rose-900/20">הסר</button>
                      </div>
                    </div>
                    <div className="grid gap-2 text-xs text-slate-200 sm:grid-cols-3">
                      <p><span className="inline-flex items-center gap-1 athena-muted">אחזקת מוסדיים: <InfoTooltip label="הסבר אחזקת מוסדיים" content={metricTooltip("institutional_pct")} /></span> {formatNumber(item.latest_snapshot?.institutional_pct)}%</p>
                      <p><span className="inline-flex items-center gap-1 athena-muted">אחזקת אינסיידרים: <InfoTooltip label="הסבר אחזקת אינסיידרים" content={metricTooltip("insider_pct")} /></span> {formatNumber(item.latest_snapshot?.insider_pct)}%</p>
                      <p><span className="inline-flex items-center gap-1 athena-muted">Relative Volume (RVOL): <InfoTooltip label="הסבר RVOL" content={metricTooltip("rvol")} /></span> {formatNumber(item.latest_snapshot?.relative_volume)}</p>
                      <p><span className="inline-flex items-center gap-1 athena-muted">נפח יומי: <InfoTooltip label="הסבר נפח יומי" content={metricTooltip("volume_today")} /></span> {formatNumber(item.latest_snapshot?.volume_today)}</p>
                      <p><span className="inline-flex items-center gap-1 athena-muted">ממוצע 30 ימים: <InfoTooltip label="הסבר ממוצע 30 ימים" content={metricTooltip("avg_volume_30d")} /></span> {formatNumber(item.latest_snapshot?.avg_volume_30d)}</p>
                      <p><span className="inline-flex items-center gap-1 athena-muted">זמן עדכון: <InfoTooltip label="הסבר זמן עדכון" content={metricTooltip("updated_at")} /></span> {formatWatchlistTime(item.last_refreshed_at)}</p>
                    </div>
                    {!isSelected && <p className="mt-2 text-xs text-slate-400 athena-muted">הכרטיס מקוצר. לחץ על הטיקר כדי להציג פירוט מלא.</p>}
                    {isSelected && (
                      <>
                        {item.last_error && <p className="mt-2 rounded border border-rose-600/40 bg-rose-900/20 px-2 py-1 text-xs text-rose-200">שגיאה אחרונה: {item.last_error}</p>}
                        {item.latest_snapshot?.top_holders?.length ? (
                          <div className="mt-2 text-xs text-slate-300">
                            <p className="inline-flex items-center gap-1 font-semibold athena-title">Top Holders <InfoTooltip label="הסבר top holders" content={metricTooltip("top_holders")} /></p>
                            <div className="space-y-1">
                              {item.latest_snapshot.top_holders.slice(0, 5).map((holder, idx) => (
                                <p key={`${item.ticker}-${holder.name}-${idx}`}>
                                  {holder.name} - מניות: {holder.shares ?? "—"} | שווי: {holder.value ?? "—"}
                                </p>
                              ))}
                            </div>
                          </div>
                        ) : null}
                      </>
                    )}
                  </article>
                );
              })
            ) : (
              <p className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-3 text-sm text-slate-300 athena-subcard athena-muted">
                עדיין אין מניות במעקב. אפשר להוסיף עד 5 מניות.
              </p>
            )}
          </div>
          <div className="space-y-4">
            <div className="rounded-xl border border-slate-700 bg-slate-950 p-3 text-sm text-slate-100 athena-subcard">
              <h3 className="mb-2 font-semibold athena-title">אירועים אחרונים</h3>
              {watchlistEvents.length === 0 && <p className="text-xs text-slate-300 athena-muted">עדיין אין אירועים.</p>}
              <div className="max-h-80 space-y-2 overflow-auto">
                {watchlistEvents.map((event) => (
                  <div key={event.id} className="rounded border border-slate-700 bg-slate-900/60 px-2 py-2 text-xs">
                    <div className="mb-1 flex items-center justify-between gap-2">
                      <span className="inline-flex items-center gap-1">
                        <span className={`rounded-full px-2 py-0.5 ${event.severity === "high" ? "border border-rose-500/40 bg-rose-950/20 text-rose-200" : event.severity === "medium" ? "border border-amber-500/40 bg-amber-950/20 text-amber-200" : "border border-slate-600 bg-slate-900 text-slate-200"}`}>
                          {eventSeverityLabel(event.severity)}
                        </span>
                        <span className={`rounded-full px-2 py-0.5 ${anomalyScoreTone(event.anomaly_score)}`}>
                          חריגות: {event.anomaly_score ?? 0}
                        </span>
                        <InfoTooltip label="הסבר ציון חריגות" content={metricTooltip("anomaly_score")} />
                      </span>
                      <span className="ltr-number text-slate-400">{formatWatchlistTime(event.created_at)}</span>
                    </div>
                    <p>{event.message}</p>
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-950 p-3 text-sm text-slate-100 athena-subcard">
              <h3 className="mb-2 font-semibold athena-title">
                היסטוריית אחזקות{selectedHistoryTicker ? ` - ${selectedHistoryTicker}` : ""}
              </h3>
              {isHistoryLoading && <p className="text-xs text-slate-300 athena-muted">טוען היסטוריה...</p>}
              {!isHistoryLoading && historySnapshots.length === 0 && <p className="text-xs text-slate-300 athena-muted">אין עדיין היסטוריה להצגה.</p>}
              <div className="max-h-80 space-y-2 overflow-auto">
                {historySnapshots.slice(0, 20).map((snapshot) => (
                  <div key={snapshot.id} className="rounded border border-slate-700 bg-slate-900/60 px-2 py-2 text-xs">
                    <p className="text-slate-300">{formatWatchlistTime(snapshot.captured_at)}</p>
                    <p>מוסדיים: {formatNumber(snapshot.institutional_pct)}%</p>
                    <p>RVOL: {formatNumber(snapshot.relative_volume)}</p>
                    <p>Volume: {formatNumber(snapshot.volume_today)}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
