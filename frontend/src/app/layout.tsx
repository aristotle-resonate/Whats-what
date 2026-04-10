import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Whats-What — City Pulse Tracker",
  description:
    "Real-time signals on trending venues, artists, events, and experiences across Austin, Dallas, San Antonio, New York, and Los Angeles.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#09090b",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full bg-zinc-950">{children}</body>
    </html>
  );
}
