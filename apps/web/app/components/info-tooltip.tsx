"use client";

import { useId, useState } from "react";

type Props = {
  label: string;
  content: string;
};

export function InfoTooltip({ label, content }: Props) {
  const tooltipId = useId();
  const [open, setOpen] = useState(false);
  return (
    <span
      className="group relative inline-flex items-center"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        aria-label={label}
        aria-describedby={tooltipId}
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-slate-500 text-[11px] font-bold text-slate-300 transition hover:border-cyan-400 hover:text-cyan-300 focus:outline-none focus:ring-2 focus:ring-cyan-400"
      >
        i
      </button>
      <span
        id={tooltipId}
        role="tooltip"
        className={`pointer-events-none absolute start-0 top-7 z-20 w-72 whitespace-pre-line rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs font-normal leading-5 text-slate-200 shadow-xl transition ${
          open ? "visible opacity-100" : "invisible opacity-0"
        }`}
      >
        {content}
      </span>
    </span>
  );
}
