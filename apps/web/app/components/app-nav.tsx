"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type NavItem = {
  href: string;
  label: string;
  shortLabel: string;
};

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "מסך ניתוח", shortLabel: "ניתוח" },
  { href: "/institutional-watchlist", label: "ניטור בעלות מוסדית", shortLabel: "ניטור" },
];

export function AppNav() {
  const pathname = usePathname();

  return (
    <nav className="athena-nav">
      <div className="athena-nav-inner">
        <div className="athena-nav-brand">
          <span className="athena-nav-brand-dot" />
          <span className="athena-nav-brand-text">Athena Invest</span>
        </div>
        <div className="athena-nav-links" role="tablist" aria-label="ניווט ראשי">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`athena-nav-link ${active ? "athena-nav-link-active" : ""}`}
                aria-current={active ? "page" : undefined}
              >
                <span className="athena-nav-link-full">{item.label}</span>
                <span className="athena-nav-link-short">{item.shortLabel}</span>
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
