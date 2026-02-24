"use client";
// CRITICAL: ConnectionGuard pattern — NO SessionProvider wrapper
import { useState, useEffect } from "react";
import { LiveKitRoom, useRoomContext, useDataChannel } from "@livekit/components-react";
import TranscriptPanel from "@/components/shared/TranscriptPanel";
import { useTranscript } from "@/hooks/livekit/useTranscript";
import TradeoffPanel from "@/components/demo/TradeoffPanel";

const LIVEKIT_URL = process.env.NEXT_PUBLIC_LIVEKIT_URL ?? "ws://localhost:7880";

interface ConnectionGuardProps {
  onPipelineStep?: (step: string | null) => void;
}

function ConnectionGuard({ onPipelineStep }: ConnectionGuardProps) {
  const turns = useTranscript();

  useDataChannel("pipeline-steps", (msg) => {
    try {
      const data = JSON.parse(new TextDecoder().decode(msg.payload));
      if (data.type === "pipeline_step") {
        onPipelineStep?.(data.step ?? null);
      }
    } catch {
      // Malformed message — ignore
    }
  });

  return <TranscriptPanel turns={turns} />;
}

interface StudentRoomProps {
  selectedQuestion?: string | null;
  onPipelineStep?: (step: string | null) => void;
}

export default function StudentRoom({ selectedQuestion, onPipelineStep }: StudentRoomProps) {
  const [token, setToken] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [showTradeoff, setShowTradeoff] = useState(false);
  const [hint, setHint] = useState<string | null>(null);

  // Show "Say this:" hint when a question is selected (voice-only room — can't inject text)
  useEffect(() => {
    if (!selectedQuestion) return;
    setHint(selectedQuestion);
    const timer = setTimeout(() => setHint(null), 10000);
    return () => clearTimeout(timer);
  }, [selectedQuestion]);

  const handleConnect = async () => {
    setConnecting(true);
    try {
      const res = await fetch(`/api/livekit-token`);
      const data = await res.json() as { token: string };
      setToken(data.token);
      setShowTradeoff(true);
    } catch (err) {
      console.error("Failed to get LiveKit token:", err);
    } finally {
      setConnecting(false);
    }
  };

  // Hint banner shown in both pre-join and joined states
  const hintBanner = hint ? (
    <div
      data-testid="say-this-hint"
      className="mb-3 p-3 bg-blue-900/40 border border-blue-500/40 rounded-lg flex items-center justify-between"
    >
      <span className="text-sm text-blue-300">
        💬 Try saying: <em className="font-medium not-italic">&ldquo;{hint}&rdquo;</em>
      </span>
      <button
        onClick={() => setHint(null)}
        className="text-gray-500 hover:text-gray-300 text-xs ml-3"
      >
        ✕
      </button>
    </div>
  ) : null;

  if (!token) {
    return (
      <div className="bg-gray-900 rounded-xl p-8 text-center">
        {hintBanner}
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
      {hintBanner}
      {/* CRITICAL: No SessionProvider — use ConnectionGuard pattern */}
      <LiveKitRoom
        token={token}
        serverUrl={LIVEKIT_URL}
        connect={true}
        audio={true}
        video={false}
        className="bg-gray-900 rounded-xl"
      >
        <ConnectionGuard onPipelineStep={onPipelineStep} />
      </LiveKitRoom>
    </div>
  );
}
