import type { Metadata } from "next";
import { Analytics } from "@vercel/analytics/next";
import { SpeedInsights } from "@vercel/speed-insights/next";
import "./globals.css";
import { AppNav } from "./components/app-nav";

const siteUrl =
  process.env.NEXT_PUBLIC_SITE_URL ??
  (process.env.VERCEL_PROJECT_PRODUCTION_URL
    ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}`
    : "https://athena-invest-ochre.vercel.app");

export const metadata: Metadata = {
  title: "Athena Invest",
  description: "ניתוח מניות מתקדם בעברית",
  metadataBase: new URL(siteUrl),
  openGraph: {
    title: "Athena Invest",
    description: "ניתוח מניות מתקדם בעברית",
    url: siteUrl,
    siteName: "Athena Invest",
    locale: "he_IL",
    type: "website",
    images: [
      {
        url: "/opengraph-image",
        width: 1200,
        height: 630,
        alt: "Athena Invest",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Athena Invest",
    description: "ניתוח מניות מתקדם בעברית",
    images: ["/twitter-image"],
  },
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
