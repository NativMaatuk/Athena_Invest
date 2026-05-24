"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  AnalysisPayload,
  ApiClientError,
  ChartPoint,
  ChatResponse,
  SuggestionItem,
  askPerplexity,
  fetchAnalysis,
  fetchChartData,
  fetchSuggestions,
} from "@/lib/api";
import { InteractivePriceChart } from "@/app/components/interactive-price-chart";
import { InfoTooltip } from "@/app/components/info-tooltip";

type TabKey = "overview" | "gaps" | "ownership";

type OwnershipHolder = {
  name?: string;
  pct_out?: string;
  shares?: string;
  value?: string;
};

function cleanLine(text: string): string {
  return text.replaceAll("**", "").replace(/\s+/g, " ").trim();
}

function analysisHighlights(text: string): string[] {
  return text
    .split("\n")
    .map((line) => cleanLine(line))
    .filter((line) => line.length > 0)
    .filter((line) => !line.includes("סטטוס נוכחי") && !line.includes("רמת סיכון"));
}

function buildPriorityInsights(analysis: AnalysisPayload): Array<{ title: string; value: string; level: "high" | "medium" | "low" }> {
  const insights: Array<{ title: string; value: string; level: "high" | "medium" | "low" }> = [];
  if (analysis.technical_signal) {
    insights.push({ title: "איתות מרכזי", value: cleanLine(analysis.technical_signal), level: "high" });
  }
  const instruction = analysisHighlights(analysis.formatted_text_he).find((line) => line.includes("הוראה:"));
  if (instruction) {
    insights.push({ title: "פעולה מומלצת", value: instruction, level: "high" });
  }
  if (analysis.risk) {
    insights.push({ title: "רמת סיכון", value: cleanLine(analysis.risk), level: "high" });
  }
  if (analysis.status) {
    insights.push({ title: "סטטוס מגמה", value: cleanLine(analysis.status), level: "medium" });
  }
  const nearest = analysis.nearest_open_gap;
  if (nearest && typeof nearest === "object") {
    const distance = nearest.distance_from_current_pct;
    if (typeof distance === "number") {
      insights.push({
        title: "גאפ קרוב",
        value: `הגאפ הקרוב במרחק ${distance.toFixed(2)}% מהמחיר הנוכחי.`,
        level: "medium",
      });
    }
  }
  const rawDays = analysis.analysis_raw?.days_until_earnings;
  if (typeof rawDays === "number") {
    insights.push({
      title: "דוחות",
      value: `נותרו ${rawDays} ימים לפרסום דוחות.`,
      level: "low",
    });
  }
  return insights.slice(0, 6);
}

function ownershipSummary(ownership: Record<string, unknown> | null | undefined): {
  overview: string[];
  holders: string[];
} {
  if (!ownership) {
    return { overview: [], holders: [] };
  }
  const overview: string[] = [];
  const holders: string[] = [];
  const institutional = ownership.institutional_pct;
  const insider = ownership.insider_pct;
  if (typeof institutional === "number") {
    overview.push(`אחזקת מוסדיים עומדת על ${institutional.toFixed(2)}%.`);
  }
  if (typeof insider === "number") {
    overview.push(`אחזקת אינסיידרים עומדת על ${insider.toFixed(2)}%.`);
  }
  const top = Array.isArray(ownership.top_holders) ? (ownership.top_holders as OwnershipHolder[]) : [];
  for (const holder of top.slice(0, 5)) {
    if (!holder?.name) {
      continue;
    }
    const details = [holder.pct_out, holder.shares ? `מניות: ${holder.shares}` : undefined, holder.value ? `שווי: ${holder.value}` : undefined]
      .filter(Boolean)
      .join(" | ");
    holders.push(details ? `${holder.name} - ${details}` : holder.name);
  }
  return { overview, holders };
}

export default function HomePage() {
  const [tickerInput, setTickerInput] = useState("");
  const [suggestions, setSuggestions] = useState<SuggestionItem[]>([]);
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [analysis, setAnalysis] = useState<AnalysisPayload | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [chartMode, setChartMode] = useState<"full" | "gaps_only">("full");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisAdminFeedback, setAnalysisAdminFeedback] = useState<string | null>(null);

  const [apiKey, setApiKey] = useState("");
  const [chatQuestion, setChatQuestion] = useState("");
  const [chatResult, setChatResult] = useState<ChatResponse | null>(null);
  const [chatError, setChatError] = useState<string | null>(null);
  const [chatAdminFeedback, setChatAdminFeedback] = useState<string | null>(null);
  const [isChatting, setIsChatting] = useState(false);

  const [chartSrc, setChartSrc] = useState<string | null>(null);
  const [chartError, setChartError] = useState<string | null>(null);
  const [isChartLoading, setIsChartLoading] = useState(false);
  const [chartPoints, setChartPoints] = useState<ChartPoint[]>([]);

  useEffect(() => {
    if (!analysis) {
      setChartSrc(null);
      setChartError(null);
      return;
    }
    const ticker = analysis.ticker;
    let active = true;
    async function loadChart() {
      setIsChartLoading(true);
      setChartError(null);
      setChartPoints([]);
      try {
        const points = await fetchChartData(ticker);
        if (active) {
          setChartPoints(points);
          setChartSrc("interactive");
        }
      } catch (error) {
        if (active) {
          setChartSrc(null);
          setChartPoints([]);
          setChartError(error instanceof Error ? error.message : "הגרף לא נטען.");
        }
      } finally {
        if (active) {
          setIsChartLoading(false);
        }
      }
    }
    void loadChart();
    return () => {
      active = false;
    };
  }, [analysis, chartMode]);

  async function onTickerInputChange(value: string) {
    setTickerInput(value);
    if (!value.trim()) {
      setSuggestions([]);
      return;
    }
    setIsSuggesting(true);
    try {
      const data = await fetchSuggestions(value);
      setSuggestions(data);
    } catch {
      setSuggestions([]);
    } finally {
      setIsSuggesting(false);
    }
  }

  async function onAnalyzeSubmit(event: FormEvent) {
    event.preventDefault();
    setAnalysisError(null);
    setAnalysisAdminFeedback(null);
    setIsAnalyzing(true);
    setAnalysis(null);
    setChartMode("full");
    try {
      const payload = await fetchAnalysis(tickerInput);
      setAnalysis(payload);
      setTickerInput(payload.ticker);
      setActiveTab("overview");
    } catch (error) {
      if (error instanceof ApiClientError) {
        setAnalysisError(error.message);
        const adminHint = `קוד: ${error.code}${error.requestId ? ` | request_id: ${error.requestId}` : ""}${
          error.adminMessage ? ` | פרטים: ${error.adminMessage}` : ""
        }`;
        setAnalysisAdminFeedback(adminHint);
      } else {
        const message = error instanceof Error ? error.message : "ניתוח הטיקר נכשל.";
        setAnalysisError(message);
      }
    } finally {
      setIsAnalyzing(false);
    }
  }

  async function onChatSubmit(event: FormEvent) {
    event.preventDefault();
    setChatError(null);
    setChatAdminFeedback(null);
    setChatResult(null);
    setIsChatting(true);
    try {
      const response = await askPerplexity(chatQuestion, apiKey, analysis?.ticker);
      setChatResult(response);
    } catch (error) {
      if (error instanceof ApiClientError) {
        setChatError(error.message);
        const adminHint = `קוד: ${error.code}${error.requestId ? ` | request_id: ${error.requestId}` : ""}${
          error.adminMessage ? ` | פרטים: ${error.adminMessage}` : ""
        }`;
        setChatAdminFeedback(adminHint);
      } else {
        const message = error instanceof Error ? error.message : "הבקשה ל-Perplexity נכשלה.";
        setChatError(message);
      }
    } finally {
      setIsChatting(false);
    }
  }

  return (
    <main className="mx-auto min-h-screen max-w-7xl px-4 py-6 sm:px-5 md:px-8 md:py-8">
      <header className="mb-6 rounded-2xl border border-slate-700 bg-slate-900/70 p-4 shadow-lg sm:p-5 md:p-6">
        <h1 className="text-2xl font-bold tracking-tight text-cyan-300 sm:text-3xl">Athena Invest</h1>
        <p className="mt-2 text-sm text-slate-200 sm:text-base">
          חפש טיקר וקבל ניתוח טכני מלא בעברית, כולל גאפים, בעלות מוסדית וגרפים.
        </p>
      </header>

      <section className="mb-8 rounded-2xl border border-slate-700 bg-slate-900/70 p-4 sm:p-5 md:p-6">
        <form className="flex flex-col gap-4 md:flex-row" onSubmit={onAnalyzeSubmit}>
          <div className="flex-1">
            <label htmlFor="ticker-input" className="mb-2 block text-sm font-medium text-slate-100">
              טיקר לחיפוש
            </label>
            <input
              id="ticker-input"
              aria-label="שדה חיפוש טיקר"
              className="w-full rounded-lg border border-slate-500 bg-slate-950 px-3 py-2 text-slate-50 outline-none ring-cyan-400 transition focus:ring-2"
              placeholder="לדוגמה: AAPL או TA35"
              value={tickerInput}
              onChange={(event) => void onTickerInputChange(event.target.value)}
            />
            {isSuggesting && <p className="mt-2 text-xs text-slate-300">טוען הצעות...</p>}
            {!isSuggesting && suggestions.length > 0 && (
              <ul className="mt-2 max-h-40 overflow-auto rounded-lg border border-slate-600 bg-slate-950">
                {suggestions.map((item) => (
                  <li key={`${item.symbol}-${item.exchange}`}>
                    <button
                      type="button"
                      className="flex w-full items-start justify-between gap-2 border-b border-slate-800 px-3 py-2 text-right hover:bg-slate-800/70"
                      onClick={() => {
                        setTickerInput(item.symbol);
                        setSuggestions([]);
                      }}
                    >
                      <span className="font-semibold text-cyan-300">{item.symbol}</span>
                      <span className="text-xs text-slate-300">
                        {item.name} | {item.exchange}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="flex items-end">
            <button
              type="submit"
              disabled={isAnalyzing || !tickerInput.trim()}
              className="w-full rounded-lg bg-cyan-500 px-6 py-2 font-semibold text-slate-950 disabled:cursor-not-allowed disabled:bg-cyan-800 md:w-auto"
            >
              {isAnalyzing ? "מנתח..." : "נתח טיקר"}
            </button>
          </div>
        </form>
        {analysisError && <p className="mt-3 text-sm text-rose-300">{analysisError}</p>}
        {analysisAdminFeedback && (
          <p className="mt-1 rounded bg-slate-950 px-2 py-1 text-xs text-amber-300">{analysisAdminFeedback}</p>
        )}
      </section>

      <section className="grid gap-6 xl:grid-cols-12">
        {analysis && (
          <article className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4 sm:p-5 md:p-6 xl:col-span-12">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-2xl font-bold text-cyan-300">{analysis.ticker}</h2>
              <span
                className={`rounded-full px-3 py-1 text-xs font-semibold ${
                  analysis.is_positive ? "bg-emerald-500/20 text-emerald-300" : "bg-rose-500/20 text-rose-300"
                }`}
              >
                כיוון: {analysis.is_positive ? "חיובי" : "שלילי"}
              </span>
            </div>
            <h3 className="mb-2 text-sm font-semibold text-cyan-300">פרופיל החברה</h3>
            <div className="grid gap-3 text-sm text-slate-100 sm:grid-cols-2 lg:grid-cols-3">
              <p className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2">
                <span className="text-slate-400">סקטור: </span>
                {analysis.company_profile.sector ?? "לא זמין"}
              </p>
              <p className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2">
                <span className="text-slate-400">תעשייה: </span>
                {analysis.company_profile.industry ?? "לא זמין"}
              </p>
              <p className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2">
                <span className="text-slate-400">שווי שוק: </span>
                {analysis.company_profile.market_cap ?? "לא זמין"}
              </p>
            </div>
            <p className="mt-3 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-300">
              {analysis.company_profile.summary ?? "אין סיכום זמין."}
            </p>
          </article>
        )}

        <article className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4 sm:p-5 md:p-6 xl:col-span-7 2xl:col-span-8">
          {analysis && <h2 className="mb-3 text-xl font-semibold text-cyan-300">{analysis.ticker}</h2>}
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <button
              type="button"
              className={`rounded-lg px-3 py-1 text-sm sm:px-4 ${
                activeTab === "overview" ? "bg-cyan-500 text-slate-950" : "bg-slate-800 text-slate-100"
              }`}
              onClick={() => setActiveTab("overview")}
            >
              כללי
            </button>
            <button
              type="button"
              className={`rounded-lg px-3 py-1 text-sm sm:px-4 ${
                activeTab === "gaps" ? "bg-cyan-500 text-slate-950" : "bg-slate-800 text-slate-100"
              }`}
              onClick={() => setActiveTab("gaps")}
            >
              גאפים
            </button>
            <button
              type="button"
              className={`rounded-lg px-3 py-1 text-sm sm:px-4 ${
                activeTab === "ownership" ? "bg-cyan-500 text-slate-950" : "bg-slate-800 text-slate-100"
              }`}
              onClick={() => setActiveTab("ownership")}
            >
              בעלות מוסדית
            </button>
          </div>

          {!analysis && <p className="text-sm text-slate-300">עדיין לא בוצע ניתוח. חפש טיקר כדי להתחיל.</p>}

          {analysis && activeTab === "overview" && (
            <div className="space-y-4">
              <div className="rounded-xl border border-slate-700 bg-slate-950 p-4">
                <h3 className="mb-2 text-sm font-semibold text-cyan-300">מה חשוב עכשיו</h3>
                <div className="space-y-2 text-sm text-slate-200">
                  {buildPriorityInsights(analysis).map((item, idx) => (
                    <div
                      key={`${item.title}-${idx}`}
                      className={`rounded border px-3 py-2 ${
                        item.level === "high"
                          ? "border-rose-400/40 bg-rose-950/20"
                          : item.level === "medium"
                            ? "border-amber-400/40 bg-amber-950/20"
                            : "border-slate-700 bg-slate-900/60"
                      }`}
                    >
                      <p className="text-xs font-semibold text-cyan-300">{item.title}</p>
                      <p>{item.value}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {analysis && activeTab === "gaps" && (
            <div className="space-y-3 text-sm text-slate-100">
              <h2 className="text-lg font-semibold text-cyan-300">מצב גאפים</h2>
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-lg border border-slate-700 bg-slate-950 p-3">
                  <p className="text-xs text-slate-400">פתוחים</p>
                  <p className="text-lg font-bold text-cyan-300">{String(analysis.gap_summary.open_count ?? 0)}</p>
                </div>
                <div className="rounded-lg border border-slate-700 bg-slate-950 p-3">
                  <p className="text-xs text-slate-400">Gap Up</p>
                  <p className="text-lg font-bold text-emerald-300">{String(analysis.gap_summary.up_count ?? 0)}</p>
                </div>
                <div className="rounded-lg border border-slate-700 bg-slate-950 p-3">
                  <p className="text-xs text-slate-400">Gap Down</p>
                  <p className="text-lg font-bold text-rose-300">{String(analysis.gap_summary.down_count ?? 0)}</p>
                </div>
              </div>
              <h3 className="text-base font-semibold">רשימת גאפים פתוחים</h3>
              <div className="space-y-2">
                {analysis.open_gaps.length === 0 && <p className="text-slate-300">אין כרגע גאפים פתוחים.</p>}
                {analysis.open_gaps.map((gap, idx) => (
                  <div key={idx} className="rounded-lg border border-slate-700 bg-slate-950 p-3 text-xs text-slate-200">
                    <p>
                      {String(gap.direction ?? "unknown")} | טווח {String(gap.zone_low ?? "-")} - {String(gap.zone_high ?? "-")}
                    </p>
                    <p>
                      תאריך: {String(gap.gap_date ?? "-")} | סטטוס: {String(gap.fill_status ?? "-")} | גודל גאפ:{" "}
                      {typeof gap.gap_size_pct === "number" ? `${gap.gap_size_pct.toFixed(2)}%` : "-"}
                    </p>
                    <p>
                      מרחק מהמחיר:{" "}
                      {typeof gap.distance_from_current_pct === "number"
                        ? `${gap.distance_from_current_pct.toFixed(2)}%`
                        : "-"}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {analysis && activeTab === "ownership" && (
            <div className="space-y-3 text-sm text-slate-100">
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-semibold text-cyan-300">בעלות מוסדית</h2>
                <InfoTooltip
                  label="הסבר על מוסדיים ואינסיידרים"
                  content="מוסדיים הם גופים גדולים כמו קרנות פנסיה, גמל ונאמנות. אינסיידרים הם הנהלה ובעלי עניין בחברה. אחוזים גבוהים של מוסדיים יכולים להעיד על אמון ארוך טווח, אבל צריך תמיד לשלב עם ניתוח טכני ופונדמנטלי."
                />
              </div>
              {analysis.ownership ? (
                <div className="space-y-2 rounded-xl border border-slate-700 bg-slate-950 p-4">
                  {ownershipSummary(analysis.ownership).overview.map((line, idx) => (
                    <p key={`overview-${idx}`} className="text-slate-100">
                      {line}
                    </p>
                  ))}
                  {ownershipSummary(analysis.ownership).holders.length > 0 && (
                    <div className="pt-2">
                      <p className="mb-1 font-semibold text-cyan-300">מחזיקים מובילים</p>
                      {ownershipSummary(analysis.ownership).holders.map((line, idx) => (
                        <p key={`holder-${idx}`} className="text-slate-200">
                          {idx + 1}. {line}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-slate-300">אין כרגע נתוני בעלות מוסדית עבור הטיקר הזה.</p>
              )}
            </div>
          )}
        </article>

        <aside className="space-y-6 xl:col-span-5 2xl:col-span-4">
          <section className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4">
            <div className="mb-3 flex items-center gap-2">
              <h2 className="text-lg font-semibold text-cyan-300">גרף אינטראקטיבי</h2>
              <InfoTooltip
                label="הסבר על רכיבי הגרף"
                content={
                  "מה רואים בגרף:\n" +
                  "• נרות יומיים - כל נר מייצג יום מסחר אחד.\n" +
                  "• SMA150 (כתום) - ממוצע נע 150 ימים לזיהוי מגמה ארוכה.\n" +
                  "• Bollinger Bands (אדום/אפור/ירוק) - רצועות תנודתיות סביב המחיר.\n" +
                  "• Volume - עמודות נפח מסחר בתחתית.\n" +
                  "• מצב 'גאפים בלבד' - סימון אזורי גאפ וגודל הגאפ באחוזים."
                }
              />
            </div>
            <div className="mb-3 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setChartMode("full")}
                className={`rounded px-3 py-1 text-xs ${chartMode === "full" ? "bg-cyan-500 text-slate-950" : "bg-slate-800 text-slate-100"}`}
              >
                גרף מלא
              </button>
              <button
                type="button"
                onClick={() => setChartMode("gaps_only")}
                className={`rounded px-3 py-1 text-xs ${
                  chartMode === "gaps_only" ? "bg-cyan-500 text-slate-950" : "bg-slate-800 text-slate-100"
                }`}
              >
                גאפים בלבד
              </button>
            </div>
            {analysis ? (
              <div className="space-y-2">
                {isChartLoading && <p className="text-xs text-slate-300">טוען גרף...</p>}
                {chartError && <p className="text-xs text-rose-300">{chartError}</p>}
                {chartSrc && <InteractivePriceChart points={chartPoints} gaps={analysis.open_gaps} mode={chartMode} />}
                <p className="text-[11px] text-slate-400">
                  אפשר לבצע זום עם הגלגלת, לגרור שמאלה/ימינה ולהגדיל את חלון האזור לקבלת תצוגה גדולה יותר.
                </p>
              </div>
            ) : (
              <p className="text-sm text-slate-300">הגרף יוצג לאחר ביצוע ניתוח.</p>
            )}
          </section>
        </aside>
      </section>

      <section className="mt-8 rounded-2xl border border-slate-700 bg-slate-900/70 p-4 sm:p-5 md:p-6">
        <h2 className="mb-3 text-xl font-semibold text-cyan-300 sm:text-2xl">צ׳אט פיננסי עם Perplexity</h2>
        <p className="mb-4 text-sm text-slate-200">
          הזן API Key אישי כדי לשאול שאלות המשך. המפתח נשמר רק בסשן הנוכחי בדפדפן ולא נשמר במסד נתונים.
        </p>
        <details className="mb-4 rounded-lg border border-slate-700 bg-slate-950 p-3 text-sm text-slate-200">
          <summary className="cursor-pointer font-semibold">איך מוציאים API Key ב-Perplexity?</summary>
          <ol className="mt-2 list-decimal space-y-1 pe-6 text-xs">
            <li>היכנס לחשבון שלך ב-Perplexity.</li>
            <li>עבור ל-API / Developer settings.</li>
            <li>צור מפתח חדש ושמור אותו אצלך באופן פרטי.</li>
            <li>הדבק כאן את המפתח כדי להפעיל את הצ׳אט.</li>
          </ol>
        </details>
        <form className="space-y-3" onSubmit={onChatSubmit}>
          <label className="block text-sm">
            <span className="mb-1 block text-slate-100">Perplexity API Key</span>
            <input
              aria-label="Perplexity API Key"
              type="password"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              className="w-full rounded-lg border border-slate-500 bg-slate-950 px-3 py-2 text-slate-50 outline-none ring-cyan-400 focus:ring-2"
              placeholder="pplx-..."
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-slate-100">שאלה פיננסית</span>
            <textarea
              aria-label="שאלה לצאט"
              value={chatQuestion}
              onChange={(event) => setChatQuestion(event.target.value)}
              className="min-h-24 w-full rounded-lg border border-slate-500 bg-slate-950 px-3 py-2 text-slate-50 outline-none ring-cyan-400 focus:ring-2"
              placeholder="לדוגמה: מה הסיכונים המרכזיים לטווח 3 חודשים בטיקר הזה?"
            />
          </label>
          <button
            type="submit"
            disabled={isChatting || !apiKey.trim() || !chatQuestion.trim()}
            className="rounded-lg bg-cyan-500 px-4 py-2 font-semibold text-slate-950 disabled:cursor-not-allowed disabled:bg-cyan-800"
          >
            {isChatting ? "שולח..." : "שאל את הצ׳אט"}
          </button>
        </form>
        {chatError && <p className="mt-3 text-sm text-rose-300">{chatError}</p>}
        {chatAdminFeedback && (
          <p className="mt-1 rounded bg-slate-950 px-2 py-1 text-xs text-amber-300">{chatAdminFeedback}</p>
        )}
        {chatResult && (
          <div className="mt-4 space-y-3 rounded-xl border border-slate-700 bg-slate-950 p-4">
            <p className="text-xs text-slate-400">מודל: {chatResult.model}</p>
            <p className="whitespace-pre-wrap text-sm text-slate-100">{chatResult.answer}</p>
            {chatResult.citations.length > 0 && (
              <div>
                <p className="mb-1 text-xs font-semibold text-cyan-300">מקורות:</p>
                <ul className="space-y-1 text-xs text-slate-300">
                  {chatResult.citations.map((item, idx) => (
                    <li key={`${item.url}-${idx}`}>
                      {item.url ? (
                        <a className="underline" href={item.url} target="_blank" rel="noreferrer">
                          {item.title || item.url}
                        </a>
                      ) : (
                        item.title || "מקור ללא קישור"
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </section>
    </main>
  );
}
