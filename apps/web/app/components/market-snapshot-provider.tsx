"use client";

import { createContext, useContext } from "react";

import type { MarketSnapshot } from "@/lib/api";

const MarketSnapshotContext = createContext<MarketSnapshot | null>(null);

type MarketSnapshotProviderProps = {
  initialSnapshot: MarketSnapshot | null;
  children: React.ReactNode;
};

export function MarketSnapshotProvider({ initialSnapshot, children }: MarketSnapshotProviderProps) {
  return <MarketSnapshotContext.Provider value={initialSnapshot}>{children}</MarketSnapshotContext.Provider>;
}

export function useInitialMarketSnapshot(): MarketSnapshot | null {
  return useContext(MarketSnapshotContext);
}
