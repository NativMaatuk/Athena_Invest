import type { Metadata } from "next";
import { Analytics } from "@vercel/analytics/next";
import { SpeedInsights } from "@vercel/speed-insights/next";
import "./globals.css";
import { AppNav } from "./components/app-nav";

export const metadata: Metadata = {
  title: "Athena Invest",
  description: "ניתוח מניות מתקדם בעברית",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="he" dir="rtl">
      <body>
        <AppNav />
        {children}
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  );
}
