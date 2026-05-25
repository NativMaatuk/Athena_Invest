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
  const rsiContainerRef = useRef<HTMLDivElement | null>(null);
  const rsiTooltipRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const rsiChartRef = useRef<IChartApi | null>(null);
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
    const rsiData: LineData[] = [];

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
      if (point.rsi != null) {
        rsiData.push({ time, value: point.rsi });
      }
    }

    const rsiMaData: LineData[] = [];
    if (rsiData.length > 0) {
      let rollingSum = 0;
      const windowValues: number[] = [];
      for (const item of rsiData) {
        const value = item.value;
        windowValues.push(value);
        rollingSum += value;
        if (windowValues.length > 14) {
          rollingSum -= windowValues.shift() ?? 0;
        }
        if (windowValues.length === 14) {
          rsiMaData.push({ time: item.time, value: rollingSum / 14 });
        }
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

    const updateRsiTooltip = (
      tooltipEl: HTMLDivElement,
      rsiValue: number | undefined,
      rsiMaValue: number | undefined,
    ) => {
      const hasBoth = rsiValue != null && rsiMaValue != null;
      const trendText = !hasBoth ? "נטרלי" : rsiValue >= rsiMaValue ? "חיובי" : "שלילי";
      tooltipEl.textContent = `RSI(14): ${rsiValue?.toFixed(2) ?? "-"} | RSI MA(14): ${
        rsiMaValue?.toFixed(2) ?? "-"
      } | מגמה: ${trendText}`;
      tooltipEl.style.color = !hasBoth ? "#cbd5e1" : rsiValue >= rsiMaValue ? "#34d399" : "#fb7185";
    };

    let cleanupRsiCrosshair: (() => void) | null = null;
    if (mode === "full" && rsiData.length > 0 && rsiContainerRef.current) {
      const rsiChart = createChart(rsiContainerRef.current, {
        width: rsiContainerRef.current.clientWidth,
        height: 180,
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
          autoScale: false,
        },
        timeScale: {
          borderColor: "#334155",
          timeVisible: true,
          secondsVisible: false,
        },
        crosshair: {
          mode: 1,
        },
      });
      rsiChartRef.current = rsiChart;

      const rsiSeries = rsiChart.addSeries(LineSeries, {
        color: "#b9bbbe",
        lineWidth: 2,
        lastValueVisible: true,
        priceLineVisible: false,
      });
      const rsiMaSeries = rsiChart.addSeries(LineSeries, {
        color: "#f59e0b",
        lineWidth: 2,
        lastValueVisible: true,
        priceLineVisible: false,
      });
      const upperThresholdSeries = rsiChart.addSeries(LineSeries, {
        color: "#ef4444",
        lineWidth: 1,
        lineStyle: 2,
        lastValueVisible: false,
        priceLineVisible: false,
      });
      const lowerThresholdSeries = rsiChart.addSeries(LineSeries, {
        color: "#22c55e",
        lineWidth: 1,
        lineStyle: 2,
        lastValueVisible: false,
        priceLineVisible: false,
      });

      rsiSeries.setData(rsiData);
      rsiMaSeries.setData(rsiMaData);
      upperThresholdSeries.setData(rsiData.map((item) => ({ time: item.time, value: 70 })));
      lowerThresholdSeries.setData(rsiData.map((item) => ({ time: item.time, value: 30 })));
      rsiChart.priceScale("right").applyOptions({
        mode: 0,
        autoScale: false,
      });
      rsiChart.timeScale().fitContent();

      const rsiTooltip = rsiTooltipRef.current;
      if (rsiTooltip) {
        const lastRsi = rsiData.at(-1)?.value;
        const lastRsiMa = rsiMaData.at(-1)?.value;
        updateRsiTooltip(rsiTooltip, lastRsi, lastRsiMa);
      }

      const onRsiCrosshairMove = (param: { point?: { x: number; y: number }; time?: unknown; seriesData: Map<unknown, unknown> }) => {
        const rsiTooltipEl = rsiTooltipRef.current;
        if (!rsiTooltipEl) {
          return;
        }
        if (!param.point || !param.time) {
          const lastRsi = rsiData.at(-1)?.value;
          const lastRsiMa = rsiMaData.at(-1)?.value;
          updateRsiTooltip(rsiTooltipEl, lastRsi, lastRsiMa);
          return;
        }

        const rsiPoint = param.seriesData.get(rsiSeries) as { value?: number } | undefined;
        const rsiMaPoint = param.seriesData.get(rsiMaSeries) as { value?: number } | undefined;
        const rsiValue = rsiPoint?.value;
        const rsiMaValue = rsiMaPoint?.value;
        updateRsiTooltip(rsiTooltipEl, rsiValue, rsiMaValue);
      };
      rsiChart.subscribeCrosshairMove(onRsiCrosshairMove);
      cleanupRsiCrosshair = () => rsiChart.unsubscribeCrosshairMove(onRsiCrosshairMove);
    }

    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry || !chartRef.current) {
        return;
      }
      chartRef.current.applyOptions({
        width: entry.contentRect.width,
        height: getChartHeight(entry.contentRect.width),
      });
      if (rsiChartRef.current) {
        rsiChartRef.current.applyOptions({
          width: entry.contentRect.width,
          height: 180,
        });
      }
    });
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      if (cleanupRsiCrosshair) {
        cleanupRsiCrosshair();
      }
      chart.remove();
      if (rsiChartRef.current) {
        rsiChartRef.current.remove();
      }
      chartRef.current = null;
      rsiChartRef.current = null;
      candleSeriesRef.current = null;
    };
  }, [points, gaps, mode]);

  if (points.length === 0) {
    return <p className="text-sm text-slate-300">אין מספיק נתונים להצגת גרף.</p>;
  }

  return (
    <div className="space-y-3">
      <div ref={containerRef} className="w-full overflow-hidden rounded-xl border border-slate-700" />
      {mode === "full" && (
        <div className="space-y-1">
          <div ref={rsiTooltipRef} className="text-xs text-slate-300" />
          <div ref={rsiContainerRef} className="w-full overflow-hidden rounded-xl border border-slate-700" />
        </div>
      )}
    </div>
  );
}
