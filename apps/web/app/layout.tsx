import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Athena Invest",
  description: "ניתוח מניות מתקדם בעברית",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="he" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
