"use client";

import { useEffect, useRef } from "react";
import {
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  createChart,
  type CandlestickData,
  type HistogramData,
  type IChartApi,
  type ISeriesApi,
  type LineData,
  type UTCTimestamp,
} from "lightweight-charts";

import type { ChartPoint } from "@/lib/api";

type GapPoint = {
  direction?: string;
  zone_low?: unknown;
  zone_high?: unknown;
  gap_size_pct?: unknown;
};

type Props = {
  points: ChartPoint[];
  gaps?: Array<Record<string, unknown>>;
  mode: "full" | "gaps_only";
};

function getChartHeight(width: number): number {
  if (width < 480) {
    return 320;
  }
  if (width < 768) {
    return 400;
  }
  if (width < 1280) {
    return 520;
  }
  return 620;
}

function toTimestamp(dateIso: string): UTCTimestamp | null {
  const date = new Date(`${dateIso}T00:00:00Z`);
  const time = Math.floor(date.getTime() / 1000);
  if (!Number.isFinite(time)) {
    return null;
  }
  return time as UTCTimestamp;
}

function toNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function InteractivePriceChart({ points, gaps = [], mode }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  useEffect(() => {
    if (!containerRef.current || points.length === 0) {
      return;
    }

    const container = containerRef.current;
    const chart = createChart(container, {
      width: container.clientWidth,
      height: getChartHeight(container.clientWidth),
      layout: {
        background: { color: "#020617" },
        textColor: "#cbd5e1",
      },
      grid: {
        vertLines: { color: "#1e293b" },
        horzLines: { color: "#1e293b" },
      },
      rightPriceScale: {
        borderColor: "#334155",
      },
      timeScale: {
        borderColor: "#334155",
      },
      crosshair: {
        mode: 1,
      },
    });
    chartRef.current = chart;

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#10b981",
      downColor: "#ef4444",
      borderVisible: false,
      wickUpColor: "#10b981",
      wickDownColor: "#ef4444",
    });
    candleSeriesRef.current = candleSeries;

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceScaleId: "volume",
      priceFormat: { type: "volume" },
      color: "#475569",
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.82, bottom: 0 },
    });

    const smaSeries = chart.addSeries(LineSeries, {
      color: "#f59e0b",
      lineWidth: 2,
    });
    const upperBandSeries = chart.addSeries(LineSeries, {
      color: "#ef4444",
      lineWidth: 1,
    });
    const middleBandSeries = chart.addSeries(LineSeries, {
      color: "#94a3b8",
      lineWidth: 1,
    });
    const lowerBandSeries = chart.addSeries(LineSeries, {
      color: "#22c55e",
      lineWidth: 1,
    });

    const candleData: CandlestickData[] = [];
    const volumeData: HistogramData[] = [];
    const smaData: LineData[] = [];
    const upperData: LineData[] = [];
    const middleData: LineData[] = [];
    const lowerData: LineData[] = [];

    for (const point of points) {
      const time = toTimestamp(point.time);
      if (!time) {
        continue;
      }
      candleData.push({
        time,
        open: point.open,
        high: point.high,
        low: point.low,
        close: point.close,
      });
      volumeData.push({
        time,
        value: point.volume ?? 0,
        color: point.close >= point.open ? "rgba(16,185,129,0.55)" : "rgba(239,68,68,0.55)",
      });
      if (point.sma_150 != null) {
        smaData.push({ time, value: point.sma_150 });
      }
      if (point.bb_upper != null) {
        upperData.push({ time, value: point.bb_upper });
      }
      if (point.bb_middle != null) {
        middleData.push({ time, value: point.bb_middle });
      }
      if (point.bb_lower != null) {
        lowerData.push({ time, value: point.bb_lower });
      }
    }

    candleSeries.setData(candleData);
    volumeSeries.setData(volumeData);
    if (mode === "full") {
      smaSeries.setData(smaData);
      upperBandSeries.setData(upperData);
      middleBandSeries.setData(middleData);
      lowerBandSeries.setData(lowerData);
    }

    if (mode === "gaps_only") {
      for (const gap of gaps as GapPoint[]) {
        const zoneLow = toNumber(gap.zone_low);
        const zoneHigh = toNumber(gap.zone_high);
        if (zoneLow == null || zoneHigh == null) {
          continue;
        }
        const color = gap.direction === "up" ? "#10b981" : "#ef4444";
        candleSeries.createPriceLine({
          price: zoneLow,
          color,
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: `Gap ${gap.direction === "up" ? "UP" : "DOWN"} ${(toNumber(gap.gap_size_pct) ?? 0).toFixed(2)}%`,
        });
        candleSeries.createPriceLine({
          price: zoneHigh,
          color,
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: false,
          title: "",
        });
      }
    }

    chart.timeScale().fitContent();

    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry || !chartRef.current) {
        return;
      }
      chartRef.current.applyOptions({
        width: entry.contentRect.width,
        height: getChartHeight(entry.contentRect.width),
      });
    });
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
    };
  }, [points, gaps, mode]);

  if (points.length === 0) {
    return <p className="text-sm text-slate-300">אין מספיק נתונים להצגת גרף.</p>;
  }

  return <div ref={containerRef} className="w-full overflow-hidden rounded-xl border border-slate-700" />;
}
