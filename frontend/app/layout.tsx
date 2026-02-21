import type { Metadata } from "next";
import "./globals.css";
// CRITICAL: Import as JS import, not CSS @import (avoids build errors with livekit styles)
import "@livekit/components-styles";

export const metadata: Metadata = {
  title: "Voice AI Tutor",
  description: "Compare LiveKit vs OpenAI Realtime architectures for AI tutoring",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-950 text-white">{children}</body>
    </html>
  );
}
