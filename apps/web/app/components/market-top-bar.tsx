"use client";

import { useEffect, useState } from "react";

import { ApiClientError, MarketSnapshot, fetchMarketSnapshot } from "@/lib/api";

function formatNumber(value: number | null | undefined, digits = 2): string {
  if (value == null || !Number.isFinite(value)) {
    return "—";
  }
  return value.toFixed(digits);
}

function formatPercent(value: number | null | undefined, digits = 2): string {
  if (value == null || !Number.isFinite(value)) {
    return "—";
  }
  if (value > 0) {
    return `+${value.toFixed(digits)}%`;
  }
  if (value < 0) {
    return `-${Math.abs(value).toFixed(digits)}%`;
  }
  return `0.${"0".repeat(Math.max(0, digits))}%`;
}

function changeColorClass(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) {
    return "text-slate-300";
  }
  if (value > 0) {
    return "text-emerald-300";
  }
  if (value < 0) {
    return "text-rose-300";
  }
  return "text-slate-200";
}

function fearGreedColorClass(score: number | null | undefined, rating: string | null | undefined): string {
  if (typeof score === "number" && Number.isFinite(score)) {
    if (score <= 25) {
      return "text-rose-300";
    }
    if (score <= 45) {
      return "text-orange-300";
    }
    if (score < 55) {
      return "text-slate-200";
    }
    if (score < 75) {
      return "text-emerald-300";
    }
    return "text-lime-300";
  }

  const normalized = (rating ?? "").toLowerCase();
  if (normalized.includes("extreme fear")) {
    return "text-rose-300";
  }
  if (normalized.includes("fear")) {
    return "text-orange-300";
  }
  if (normalized.includes("extreme greed")) {
    return "text-lime-300";
  }
  if (normalized.includes("greed")) {
    return "text-emerald-300";
  }
  return "text-slate-200";
}

export function MarketTopBar() {
  const [snapshot, setSnapshot] = useState<MarketSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    const loadSnapshot = async () => {
      try {
        const payload = await fetchMarketSnapshot();
        if (!active) {
          return;
        }
        setSnapshot(payload);
        setError(null);
      } catch (err) {
        if (!active) {
          return;
        }
        const fallbackMessage = "נתוני שוק לא זמינים כרגע.";
        if (err instanceof ApiClientError) {
          setError(err.message || fallbackMessage);
        } else if (err instanceof Error) {
          setError(err.message || fallbackMessage);
        } else {
          setError(fallbackMessage);
        }
      }
    };

    void loadSnapshot();
    const dataInterval = window.setInterval(() => {
      void loadSnapshot();
    }, 5 * 60 * 1000);

    return () => {
      active = false;
      window.clearInterval(dataInterval);
    };
  }, []);

  const marketItems = (
    <>
      <span className="shrink-0 text-cyan-300">
        דולר/שקל: {formatNumber(snapshot?.usd_ils, 4)}{" "}
        <span className={`ltr-number ${changeColorClass(snapshot?.usd_ils_change_pct)}`}>
          ({formatPercent(snapshot?.usd_ils_change_pct)})
        </span>
      </span>
      <span className={`shrink-0 ${fearGreedColorClass(snapshot?.fear_greed_score, snapshot?.fear_greed_rating)}`}>
        Fear &amp; Greed: {formatNumber(snapshot?.fear_greed_score, 0)}
        {snapshot?.fear_greed_rating ? ` (${snapshot.fear_greed_rating})` : ""}
      </span>
      <span className="shrink-0 text-fuchsia-300">VIX: {formatNumber(snapshot?.vix, 2)}</span>
      <span className={`shrink-0 ${changeColorClass(snapshot?.spy_change_pct)}`}>
        SPY: <span className="ltr-number">{formatPercent(snapshot?.spy_change_pct)}</span>
      </span>
      <span className={`shrink-0 ${changeColorClass(snapshot?.qqq_change_pct)}`}>
        QQQ: <span className="ltr-number">{formatPercent(snapshot?.qqq_change_pct)}</span>
      </span>
      {snapshot?.updated_at_local && <span className="shrink-0 text-slate-400">עודכן: {snapshot.updated_at_local}</span>}
    </>
  );

  return (
    <section className="sticky top-0 z-30 mb-4 rounded-xl border border-cyan-600/30 bg-slate-950/95 px-3 py-2 shadow-lg backdrop-blur">
      <div className="market-marquee text-xs sm:text-sm">
        <div className="market-marquee-track">
          <div className="market-marquee-group">{marketItems}</div>
          <div className="market-marquee-group" aria-hidden="true">
            {marketItems}
          </div>
        </div>
      </div>
      {error && <p className="mt-1 text-xs text-rose-300">{error}</p>}
    </section>
  );
}
