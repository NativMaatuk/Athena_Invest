"use client";

import { useEffect, useRef, useState } from "react";
import {
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  createTextWatermark,
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
  theme?: "dark" | "light";
  ticker?: string;
};

function getChartHeight(width: number, sizeMode: "responsive" | "expanded"): number {
  const extra = sizeMode === "expanded" ? 130 : 0;
  if (width < 480) {
    return 360 + extra;
  }
  if (width < 768) {
    return 480 + extra;
  }
  if (width < 1280) {
    return 640 + extra;
  }
  return 780 + extra;
}

function getRsiHeight(sizeMode: "responsive" | "expanded"): number {
  return sizeMode === "expanded" ? 220 : 180;
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

export function InteractivePriceChart({
  points,
  gaps = [],
  mode,
  theme = "dark",
  ticker = "",
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const rsiContainerRef = useRef<HTMLDivElement | null>(null);
  const rsiTooltipRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const rsiChartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [sizeMode, setSizeMode] = useState<"responsive" | "expanded">("responsive");

  const exportChartImage = async () => {
    const chart = chartRef.current;
    if (!chart) {
      return;
    }
    setIsExporting(true);
    try {
      const mainCanvas = chart.takeScreenshot(true, false);
      let finalCanvas = mainCanvas;

      if (mode === "full" && rsiChartRef.current) {
        const rsiCanvas = rsiChartRef.current.takeScreenshot(true, false);
        const gap = 10;
        const merged = document.createElement("canvas");
        merged.width = Math.max(mainCanvas.width, rsiCanvas.width);
        merged.height = mainCanvas.height + rsiCanvas.height + gap;
        const ctx = merged.getContext("2d");
        if (ctx) {
          ctx.fillStyle = theme === "light" ? "#ffffff" : "#110d22";
          ctx.fillRect(0, 0, merged.width, merged.height);
          ctx.drawImage(mainCanvas, 0, 0);
          ctx.drawImage(rsiCanvas, 0, mainCanvas.height + gap);
          finalCanvas = merged;
        }
      }

      const blob = await new Promise<Blob | null>((resolve) => finalCanvas.toBlob(resolve, "image/png"));
      if (!blob) {
        return;
      }
      const fileName = `athena-chart-${new Date().toISOString().replace(/[:.]/g, "-")}.png`;
      const file = new File([blob], fileName, { type: "image/png" });

      if (navigator.share && navigator.canShare?.({ files: [file] })) {
        try {
          await navigator.share({ files: [file], title: "Athena chart" });
          return;
        } catch {
          // Fallback to download
        }
      }

      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } finally {
      setIsExporting(false);
    }
  };

  useEffect(() => {
    if (!containerRef.current || points.length === 0) {
      return;
    }

    const palette =
      theme === "light"
        ? {
            background: "#ffffff",
            text: "#261b44",
            grid: "#e2def7",
            border: "#d8cff8",
            accent: "#7c3aed",
            up: "#059669",
            down: "#e11d48",
            neutral: "#8b82b2",
            info: "#0369a1",
            warning: "#b45309",
            watermark: "rgba(124, 58, 237, 0.12)",
          }
        : {
            background: "#110d22",
            text: "#d9d1ff",
            grid: "#2a2246",
            border: "#3a2f63",
            accent: "#a78bfa",
            up: "#34d399",
            down: "#fb7185",
            neutral: "#8f84be",
            info: "#67e8f9",
            warning: "#f59e0b",
            watermark: "rgba(167, 139, 250, 0.14)",
          };

    const container = containerRef.current;
    const initialWidth = Math.max(320, container.clientWidth);
    const initialMainHeight = getChartHeight(initialWidth, sizeMode);
    const initialRsiHeight = getRsiHeight(sizeMode);
    const chart = createChart(container, {
      autoSize: false,
      width: initialWidth,
      height: initialMainHeight,
      layout: {
        background: { color: palette.background },
        textColor: palette.text,
      },
      grid: {
        vertLines: { color: palette.grid },
        horzLines: { color: palette.grid },
      },
      rightPriceScale: {
        borderColor: palette.border,
      },
      timeScale: {
        borderColor: palette.border,
      },
      crosshair: {
        mode: 1,
      },
    });
    chartRef.current = chart;
    if (ticker.trim()) {
      createTextWatermark(chart.panes()[0], {
        horzAlign: "center",
        vertAlign: "center",
        lines: [
          {
            text: ticker.trim().toUpperCase(),
            color: palette.watermark,
            fontSize: initialWidth < 768 ? 44 : 72,
            fontStyle: "bold",
          },
        ],
      });
    }

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: palette.up,
      downColor: palette.down,
      borderVisible: false,
      wickUpColor: palette.up,
      wickDownColor: palette.down,
    });
    candleSeriesRef.current = candleSeries;

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceScaleId: "volume",
      priceFormat: { type: "volume" },
      color: palette.neutral,
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.82, bottom: 0 },
    });

    const smaSeries = chart.addSeries(LineSeries, {
      color: palette.warning,
      lineWidth: 2,
    });
    const upperBandSeries = chart.addSeries(LineSeries, {
      color: palette.down,
      lineWidth: 1,
    });
    const middleBandSeries = chart.addSeries(LineSeries, {
      color: palette.neutral,
      lineWidth: 1,
    });
    const lowerBandSeries = chart.addSeries(LineSeries, {
      color: palette.up,
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
        color: point.close >= point.open ? "rgba(52,211,153,0.55)" : "rgba(251,113,133,0.55)",
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
        const color = gap.direction === "up" ? palette.up : palette.down;
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
      tooltipEl.style.color = !hasBoth ? palette.text : rsiValue >= rsiMaValue ? palette.up : palette.down;
    };

    let cleanupRsiCrosshair: (() => void) | null = null;
    let cleanupRangeSync: (() => void) | null = null;
    if (mode === "full" && rsiData.length > 0 && rsiContainerRef.current) {
      const rsiChart = createChart(rsiContainerRef.current, {
        autoSize: false,
        width: Math.max(320, rsiContainerRef.current.clientWidth),
        height: initialRsiHeight,
        layout: {
          background: { color: palette.background },
          textColor: palette.text,
        },
        grid: {
          vertLines: { color: palette.grid },
          horzLines: { color: palette.grid },
        },
        rightPriceScale: {
          borderColor: palette.border,
          autoScale: false,
        },
        timeScale: {
          borderColor: palette.border,
          timeVisible: true,
          secondsVisible: false,
        },
        crosshair: {
          mode: 1,
        },
      });
      rsiChartRef.current = rsiChart;

      const rsiSeries = rsiChart.addSeries(LineSeries, {
        color: palette.neutral,
        lineWidth: 2,
        lastValueVisible: true,
        priceLineVisible: false,
      });
      const rsiMaSeries = rsiChart.addSeries(LineSeries, {
        color: palette.warning,
        lineWidth: 2,
        lastValueVisible: true,
        priceLineVisible: false,
      });
      const upperThresholdSeries = rsiChart.addSeries(LineSeries, {
        color: palette.down,
        lineWidth: 1,
        lineStyle: 2,
        lastValueVisible: false,
        priceLineVisible: false,
      });
      const lowerThresholdSeries = rsiChart.addSeries(LineSeries, {
        color: palette.up,
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

      let syncingRange = false;
      const syncPriceToRsi = (range: unknown) => {
        if (!range || syncingRange) {
          return;
        }
        syncingRange = true;
        rsiChart.timeScale().setVisibleLogicalRange(range as never);
        syncingRange = false;
      };
      const syncRsiToPrice = (range: unknown) => {
        if (!range || syncingRange) {
          return;
        }
        syncingRange = true;
        chart.timeScale().setVisibleLogicalRange(range as never);
        syncingRange = false;
      };
      chart.timeScale().subscribeVisibleLogicalRangeChange(syncPriceToRsi);
      rsiChart.timeScale().subscribeVisibleLogicalRangeChange(syncRsiToPrice);
      cleanupRangeSync = () => {
        chart.timeScale().unsubscribeVisibleLogicalRangeChange(syncPriceToRsi);
        rsiChart.timeScale().unsubscribeVisibleLogicalRangeChange(syncRsiToPrice);
      };
    }

    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry || !chartRef.current) {
        return;
      }
      const nextWidth = Math.max(320, entry.contentRect.width);
      const nextMainHeight = getChartHeight(nextWidth, sizeMode);
      chartRef.current.applyOptions({
        width: nextWidth,
        height: nextMainHeight,
      });
      if (rsiChartRef.current) {
        rsiChartRef.current.applyOptions({
          width: nextWidth,
          height: getRsiHeight(sizeMode),
        });
      }
    });
    resizeObserver.observe(container);

    const onWindowResize = () => {
      if (!containerRef.current || !chartRef.current) {
        return;
      }
      const width = Math.max(320, containerRef.current.clientWidth);
      chartRef.current.applyOptions({
        width,
        height: getChartHeight(width, sizeMode),
      });
      if (rsiChartRef.current) {
        rsiChartRef.current.applyOptions({
          width,
          height: getRsiHeight(sizeMode),
        });
      }
    };
    window.addEventListener("resize", onWindowResize);
    onWindowResize();

    return () => {
      window.removeEventListener("resize", onWindowResize);
      resizeObserver.disconnect();
      if (cleanupRsiCrosshair) {
        cleanupRsiCrosshair();
      }
      if (cleanupRangeSync) {
        cleanupRangeSync();
      }
      chart.remove();
      if (rsiChartRef.current) {
        rsiChartRef.current.remove();
      }
      chartRef.current = null;
      rsiChartRef.current = null;
      candleSeriesRef.current = null;
    };
  }, [points, gaps, mode, theme, ticker, sizeMode]);
  if (points.length === 0) {
    return <p className="text-sm text-slate-300 athena-muted">אין מספיק נתונים להצגת גרף.</p>;
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setSizeMode("responsive")}
            className={`rounded px-3 py-1 text-xs athena-tab-btn ${sizeMode === "responsive" ? "athena-tab-btn-active" : ""}`}
          >
            Auto
          </button>
          <button
            type="button"
            onClick={() => setSizeMode("expanded")}
            className={`rounded px-3 py-1 text-xs athena-tab-btn ${sizeMode === "expanded" ? "athena-tab-btn-active" : ""}`}
          >
            Expanded
          </button>
        </div>
        <button
          type="button"
          onClick={() => void exportChartImage()}
          disabled={isExporting}
          className="rounded-md border border-slate-500 bg-slate-950 px-3 py-1 text-xs font-semibold text-slate-100 transition hover:border-violet-400 hover:text-violet-300 disabled:cursor-not-allowed disabled:opacity-60 athena-toggle-btn"
        >
          {isExporting ? "מכין צילום..." : "צילום גרף"}
        </button>
      </div>
      <div ref={containerRef} className="w-full overflow-hidden rounded-xl border border-slate-700 athena-subcard" />
      {mode === "full" && (
        <div className="space-y-1">
          <div ref={rsiTooltipRef} className="text-xs text-slate-300 athena-muted" />
          <div ref={rsiContainerRef} className="w-full overflow-hidden rounded-xl border border-slate-700 athena-subcard" />
        </div>
      )}
    </div>
  );
}
