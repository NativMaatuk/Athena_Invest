import "server-only";

import type { MarketSnapshot } from "@/lib/api";

function apiBaseUrl(): string | null {
  return process.env.API_CRON_TARGET_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? null;
}

export async function fetchInitialMarketSnapshot(): Promise<MarketSnapshot | null> {
  const base = apiBaseUrl();
  if (!base) {
    return null;
  }
  try {
    const response = await fetch(`${base}/api/v1/market/snapshot`, {
      method: "GET",
      cache: "no-store",
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as MarketSnapshot;
  } catch {
    return null;
  }
}
