"use client";

import { useEffect, useRef, useState } from "react";

import {
  ApiClientError,
  MarketSnapshot,
  fetchActiveUsers,
  fetchMarketSnapshot,
  sendPresenceHeartbeat,
} from "@/lib/api";
import { useInitialMarketSnapshot } from "@/app/components/market-snapshot-provider";
import { marketRefreshIntervalMs } from "@/lib/market-hours";

const PRESENCE_REFRESH_MS = 45_000;
const PRESENCE_STORAGE_KEY = "athena-presence-session-id";
const DRAG_START_THRESHOLD_PX = 8;

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
    return "athena-muted";
  }
  if (value > 0) {
    return "athena-positive";
  }
  if (value < 0) {
    return "athena-negative";
  }
  return "athena-text";
}

function fearGreedColorClass(score: number | null | undefined, rating: string | null | undefined): string {
  if (typeof score === "number" && Number.isFinite(score)) {
    if (score <= 25) {
      return "athena-negative";
    }
    if (score <= 45) {
      return "athena-warning";
    }
    if (score < 55) {
      return "athena-text";
    }
    if (score < 75) {
      return "athena-positive";
    }
    return "athena-info";
  }

  const normalized = (rating ?? "").toLowerCase();
  if (normalized.includes("extreme fear")) {
    return "athena-negative";
  }
  if (normalized.includes("fear")) {
    return "athena-warning";
  }
  if (normalized.includes("extreme greed")) {
    return "athena-info";
  }
  if (normalized.includes("greed")) {
    return "athena-positive";
  }
  return "athena-text";
}

type MarketTopBarProps = {
  onActiveUsersChange?: (count: number | null) => void;
  initialSnapshot?: MarketSnapshot | null;
};

export function MarketTopBar({ onActiveUsersChange, initialSnapshot = null }: MarketTopBarProps) {
  const contextSnapshot = useInitialMarketSnapshot();
  const resolvedInitialSnapshot = initialSnapshot ?? contextSnapshot ?? null;
  const [snapshot, setSnapshot] = useState<MarketSnapshot | null>(resolvedInitialSnapshot);
  const [activeUsers, setActiveUsers] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const marqueeViewportRef = useRef<HTMLDivElement | null>(null);
  const marqueeTrackRef = useRef<HTMLDivElement | null>(null);
  const marqueeGroupRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let active = true;
    let timeoutId: number | null = null;
    let retryAttempt = 0;

    const retryDelaysMs = [1500, 4000];

    const scheduleNext = (delayMs: number) => {
      if (!active) {
        return;
      }
      if (timeoutId != null) {
        window.clearTimeout(timeoutId);
      }
      timeoutId = window.setTimeout(() => {
        void loadSnapshot();
      }, delayMs);
    };

    const loadSnapshot = async () => {
      try {
        const payload = await fetchMarketSnapshot();
        if (!active) {
          return;
        }
        setSnapshot(payload);
        setError(null);
        retryAttempt = 0;
        scheduleNext(marketRefreshIntervalMs());
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
        if (retryAttempt < retryDelaysMs.length) {
          const delayMs = retryDelaysMs[retryAttempt];
          retryAttempt += 1;
          scheduleNext(delayMs);
          return;
        }
        retryAttempt = 0;
        scheduleNext(marketRefreshIntervalMs());
      }
    };

    void loadSnapshot();

    return () => {
      active = false;
      if (timeoutId != null) {
        window.clearTimeout(timeoutId);
      }
    };
  }, []);

  useEffect(() => {
    onActiveUsersChange?.(activeUsers);
  }, [activeUsers, onActiveUsersChange]);

  useEffect(() => {
    let active = true;

    const getOrCreateSessionId = (): string => {
      const existing = window.localStorage.getItem(PRESENCE_STORAGE_KEY);
      if (existing && existing.length >= 8) {
        return existing;
      }
      const nextId =
        typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
          ? crypto.randomUUID()
          : `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
      window.localStorage.setItem(PRESENCE_STORAGE_KEY, nextId);
      return nextId;
    };

    const refreshPresence = async () => {
      const sessionId = getOrCreateSessionId();
      try {
        const heartbeat = await sendPresenceHeartbeat(sessionId);
        if (!active) {
          return;
        }
        setActiveUsers(heartbeat.active_users);
      } catch {
        // Keep UI resilient if heartbeat fails.
      }

      try {
        const current = await fetchActiveUsers();
        if (!active) {
          return;
        }
        setActiveUsers(current.active_users);
      } catch {
        // Keep last known value.
      }
    };

    void refreshPresence();
    const intervalId = window.setInterval(() => {
      void refreshPresence();
    }, PRESENCE_REFRESH_MS);

    return () => {
      active = false;
      window.clearInterval(intervalId);
    };
  }, []);

  useEffect(() => {
    const viewport = marqueeViewportRef.current;
    const track = marqueeTrackRef.current;
    const firstGroup = marqueeGroupRef.current;
    if (!viewport || !track || !firstGroup) {
      return;
    }

    let rafId = 0;
    let running = true;
    let viewportWidth = 0;
    let loopWidth = 0;
    let offsetX = 0;
    let lastFrameTs = performance.now();
    let isDragging = false;
    let isHorizontalDrag = false;
    let pointerId: number | null = null;
    let hasPointerCapture = false;
    let dragStartX = 0;
    let dragStartY = 0;
    let lastPointerX = 0;
    let lastPointerTs = 0;
    let inertialVelocity = 0;
    let reducedMotion = false;
    const autoVelocity = -32;

    const reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onReducedMotionChange = () => {
      reducedMotion = reducedMotionQuery.matches;
      if (reducedMotion) {
        inertialVelocity = 0;
      }
    };
    onReducedMotionChange();
    reducedMotionQuery.addEventListener("change", onReducedMotionChange);

    const draw = () => {
      track.style.transform = `translate3d(${offsetX}px, 0, 0)`;
    };

    const recalcDimensions = () => {
      viewportWidth = Math.ceil(viewport.getBoundingClientRect().width);
      const groupRect = firstGroup.getBoundingClientRect();
      loopWidth = Math.max(firstGroup.offsetWidth, Math.ceil(groupRect.width));
      if (loopWidth <= 1 || !Number.isFinite(loopWidth) || viewportWidth <= 1 || !Number.isFinite(viewportWidth)) {
        offsetX = 0;
        inertialVelocity = 0;
        draw();
        return;
      }
      if (offsetX < -loopWidth || offsetX > viewportWidth) {
        offsetX = viewportWidth;
      }
      draw();
    };

    const groupResizeObserver = new ResizeObserver(recalcDimensions);
    groupResizeObserver.observe(firstGroup);
    groupResizeObserver.observe(viewport);
    recalcDimensions();
    if (viewportWidth > 1) {
      offsetX = viewportWidth;
      draw();
    }

    const stopDrag = () => {
      isDragging = false;
      isHorizontalDrag = false;
      pointerId = null;
      hasPointerCapture = false;
      track.classList.remove("is-dragging");
      if (reducedMotion) {
        inertialVelocity = 0;
      }
    };

    const onPointerDown = (event: PointerEvent) => {
      pointerId = event.pointerId;
      isDragging = true;
      isHorizontalDrag = false;
      inertialVelocity = 0;
      dragStartX = event.clientX;
      dragStartY = event.clientY;
      lastPointerX = event.clientX;
      lastPointerTs = performance.now();
    };

    const onPointerMove = (event: PointerEvent) => {
      if (!isDragging || pointerId !== event.pointerId) {
        return;
      }

      const totalDeltaX = event.clientX - dragStartX;
      const totalDeltaY = event.clientY - dragStartY;
      if (!isHorizontalDrag) {
        const horizontalPastThreshold = Math.abs(totalDeltaX) >= DRAG_START_THRESHOLD_PX;
        const horizontalDominant = Math.abs(totalDeltaX) > Math.abs(totalDeltaY);
        if (!horizontalPastThreshold || !horizontalDominant) {
          if (Math.abs(totalDeltaY) >= DRAG_START_THRESHOLD_PX && Math.abs(totalDeltaY) > Math.abs(totalDeltaX)) {
            stopDrag();
          }
          return;
        }
        isHorizontalDrag = true;
        track.classList.add("is-dragging");
        if (!hasPointerCapture) {
          track.setPointerCapture(event.pointerId);
          hasPointerCapture = true;
        }
      }

      if (event.cancelable) {
        event.preventDefault();
      }
      const now = performance.now();
      const deltaX = event.clientX - lastPointerX;
      const deltaT = Math.max(8, now - lastPointerTs);
      offsetX += deltaX;
      if (loopWidth > 1 && Number.isFinite(loopWidth) && viewportWidth > 1 && Number.isFinite(viewportWidth)) {
        if (offsetX <= -loopWidth || offsetX > viewportWidth) {
          offsetX = viewportWidth;
        }
      }
      inertialVelocity = (deltaX / deltaT) * 1000;
      lastPointerX = event.clientX;
      lastPointerTs = now;
      draw();
    };

    const onPointerUp = (event: PointerEvent) => {
      if (pointerId !== event.pointerId) {
        return;
      }
      if (hasPointerCapture) {
        track.releasePointerCapture(event.pointerId);
      }
      stopDrag();
    };

    const onPointerCancel = (event: PointerEvent) => {
      if (pointerId !== event.pointerId) {
        return;
      }
      stopDrag();
    };

    const onWindowBlur = () => {
      if (isDragging) {
        stopDrag();
      }
    };

    const onWindowResize = () => {
      recalcDimensions();
    };

    const visualViewport = window.visualViewport;
    const onVisualViewportResize = () => {
      recalcDimensions();
    };
    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        recalcDimensions();
      }
    };

    const tick = (now: number) => {
      if (!running) {
        return;
      }
      const dt = Math.min(34, now - lastFrameTs) / 1000;
      lastFrameTs = now;

      if (loopWidth <= 1 || !Number.isFinite(loopWidth) || viewportWidth <= 1 || !Number.isFinite(viewportWidth)) {
        offsetX = 0;
        inertialVelocity = 0;
        draw();
        rafId = window.requestAnimationFrame(tick);
        return;
      }

      if (!isDragging) {
        if (Math.abs(inertialVelocity) > 8 && !reducedMotion) {
          offsetX += inertialVelocity * dt;
          inertialVelocity *= Math.pow(0.9, dt * 60);
        } else {
          inertialVelocity = 0;
          if (!reducedMotion) {
            offsetX += autoVelocity * dt;
          }
        }
      }
      if (offsetX <= -loopWidth) {
        offsetX = viewportWidth;
      } else if (offsetX > viewportWidth) {
        offsetX = viewportWidth;
      }
      draw();
      rafId = window.requestAnimationFrame(tick);
    };

    track.addEventListener("pointerdown", onPointerDown);
    track.addEventListener("pointermove", onPointerMove);
    track.addEventListener("pointerup", onPointerUp);
    track.addEventListener("pointercancel", onPointerCancel);
    track.addEventListener("lostpointercapture", stopDrag);
    window.addEventListener("blur", onWindowBlur);
    window.addEventListener("resize", onWindowResize);
    visualViewport?.addEventListener("resize", onVisualViewportResize);
    document.addEventListener("visibilitychange", onVisibilityChange);
    rafId = window.requestAnimationFrame(tick);

    return () => {
      running = false;
      window.cancelAnimationFrame(rafId);
      groupResizeObserver.disconnect();
      track.removeEventListener("pointerdown", onPointerDown);
      track.removeEventListener("pointermove", onPointerMove);
      track.removeEventListener("pointerup", onPointerUp);
      track.removeEventListener("pointercancel", onPointerCancel);
      track.removeEventListener("lostpointercapture", stopDrag);
      window.removeEventListener("blur", onWindowBlur);
      window.removeEventListener("resize", onWindowResize);
      visualViewport?.removeEventListener("resize", onVisualViewportResize);
      document.removeEventListener("visibilitychange", onVisibilityChange);
      reducedMotionQuery.removeEventListener("change", onReducedMotionChange);
    };
  }, []);

  const marketItems = (
    <>
      <span className="shrink-0 athena-info">
        דולר/שקל: {formatNumber(snapshot?.usd_ils, 4)}{" "}
        <span className={`ltr-number ${changeColorClass(snapshot?.usd_ils_change_pct)}`}>
          ({formatPercent(snapshot?.usd_ils_change_pct)})
        </span>
      </span>
      <span className={`shrink-0 ${fearGreedColorClass(snapshot?.fear_greed_score, snapshot?.fear_greed_rating)}`}>
        Fear &amp; Greed: {formatNumber(snapshot?.fear_greed_score, 0)}
        {snapshot?.fear_greed_rating ? ` (${snapshot.fear_greed_rating})` : ""}
      </span>
      <span className="shrink-0 athena-title">VIX: {formatNumber(snapshot?.vix, 2)}</span>
      <span className={`shrink-0 ${changeColorClass(snapshot?.spy_change_pct)}`}>
        SPY: <span className="ltr-number">{formatPercent(snapshot?.spy_change_pct)}</span>
      </span>
      <span className={`shrink-0 ${changeColorClass(snapshot?.qqq_change_pct)}`}>
        QQQ: <span className="ltr-number">{formatPercent(snapshot?.qqq_change_pct)}</span>
      </span>
      {snapshot?.updated_at_local && <span className="shrink-0 athena-muted">עודכן: {snapshot.updated_at_local}</span>}
    </>
  );

  return (
    <section className="sticky top-0 z-30 mb-4 rounded-xl border px-3 py-2 shadow-lg backdrop-blur athena-card athena-topbar">
      <div ref={marqueeViewportRef} className="market-marquee text-xs sm:text-sm" aria-label="market ticker draggable">
        <div ref={marqueeTrackRef} className="market-marquee-track">
          <div ref={marqueeGroupRef} className="market-marquee-group athena-marquee-divider">
            {marketItems}
          </div>
        </div>
      </div>
      {error && <p className="mt-1 text-xs athena-negative">{error}</p>}
    </section>
  );
}
