"use client";
// CRITICAL: ConnectionGuard pattern — NO SessionProvider wrapper
import { useState } from "react";
import { LiveKitRoom, useRoomContext } from "@livekit/components-react";
import TranscriptPanel from "@/components/shared/TranscriptPanel";
import { useTranscript } from "@/hooks/livekit/useTranscript";
import TradeoffPanel from "@/components/demo/TradeoffPanel";

const LIVEKIT_URL = process.env.NEXT_PUBLIC_LIVEKIT_URL ?? "ws://localhost:7880";

function ConnectionGuard() {
  const turns = useTranscript();
  return <TranscriptPanel turns={turns} />;
}

export default function StudentRoom() {
  const [token, setToken] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [showTradeoff, setShowTradeoff] = useState(false);

  const handleConnect = async () => {
    setConnecting(true);
    try {
      // In production, fetch token from agent-a service
      // For demo, use a placeholder flow
      const res = await fetch(`/api/livekit-token`);
      const data = await res.json();
      setToken(data.token);
      setShowTradeoff(true);
    } catch (err) {
      console.error("Failed to get LiveKit token:", err);
    } finally {
      setConnecting(false);
    }
  };

  if (!token) {
    return (
      <div className="bg-gray-900 rounded-xl p-8 text-center">
        <p className="text-gray-400 mb-4 text-sm">
          Version A uses LiveKit rooms for multi-participant WebRTC with pipeline STT→LLM→TTS.
        </p>
        <button
          onClick={handleConnect}
          disabled={connecting}
          className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg py-2 px-6 font-medium transition-colors"
        >
          {connecting ? "Connecting..." : "Join LiveKit Room"}
        </button>
      </div>
    );
  }

  return (
    <div>
      {showTradeoff && (
        <TradeoffPanel trigger="english" onDismiss={() => setShowTradeoff(false)} />
      )}
      {/* CRITICAL: No SessionProvider — use ConnectionGuard pattern */}
      <LiveKitRoom
        token={token}
        serverUrl={LIVEKIT_URL}
        connect={true}
        audio={true}
        video={false}
        className="bg-gray-900 rounded-xl"
      >
        <ConnectionGuard />
      </LiveKitRoom>
    </div>
  );
}
