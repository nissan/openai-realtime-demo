"use client";
import { useState, useMemo, useCallback, useEffect } from "react";
import { useRealtimeSession } from "@/hooks/openai/useRealtimeSession";
import { useBackendTts } from "@/hooks/openai/useBackendTts";
import TradeoffPanel from "@/components/demo/TradeoffPanel";
import TranscriptPanel from "@/components/shared/TranscriptPanel";
import EscalationBanner from "@/components/shared/EscalationBanner";
import type { TranscriptTurn } from "@/components/shared/TranscriptPanel";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_B_URL ?? "http://localhost:8001";

interface RealtimeSessionProps {
  selectedQuestion?: string | null;
  onPipelineStep?: (step: string | null) => void;
}

export default function RealtimeSession({ selectedQuestion, onPipelineStep }: RealtimeSessionProps) {
  // Stable session ID for the lifetime of this component
  const sessionId = useMemo(() => crypto.randomUUID(), []);

  const [turns, setTurns] = useState<TranscriptTurn[]>([]);
  const [showFillerTradeoff, setShowFillerTradeoff] = useState(false);
  const [escalated, setEscalated] = useState(false);

  const { ttsState, playJobAudio } = useBackendTts(BACKEND_URL);

  const dispatchToOrchestrator = useCallback(async (studentText: string) => {
    try {
      const dispatchRes = await fetch(`${BACKEND_URL}/orchestrate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, student_text: studentText }),
      });
      if (!dispatchRes.ok) {
        console.error("Orchestrate dispatch failed:", dispatchRes.status);
        return;
      }
      const { job_id } = await dispatchRes.json() as { job_id: string };

      // Job dispatched — specialist is processing
      onPipelineStep?.("specialist");

      const jobRes = await fetch(`${BACKEND_URL}/orchestrate/${job_id}/wait`, { method: "POST" });
      if (!jobRes.ok) {
        console.error("Orchestrate wait failed:", jobRes.status);
        onPipelineStep?.(null);
        return;
      }
      const job = await jobRes.json() as {
        tts_ready: boolean;
        subject: string | null;
        job_id: string;
      };

      // Specialist complete — guardrail applied
      onPipelineStep?.("guardrail");

      if (job.tts_ready) {
        onPipelineStep?.("tts");
        await playJobAudio(job_id, sessionId);
      }
      if (job.subject === "escalate") setEscalated(true);
    } catch (err) {
      console.error("Orchestrator dispatch error:", err);
    } finally {
      onPipelineStep?.(null);
    }
  }, [sessionId, playJobAudio, onPipelineStep]);

  const { connectionState, connect, disconnect, sendText } = useRealtimeSession(
    BACKEND_URL,
    sessionId,
    {
      onTranscript: (speaker, text) => {
        setTurns((prev) => [
          ...prev,
          { speaker, text, timestamp: new Date() },
        ]);
      },
      onToolCall: (name, args) => {
        if (name === "dispatch_to_orchestrator" && typeof args.student_text === "string") {
          dispatchToOrchestrator(args.student_text);
        }
      },
    }
  );

  // When selectedQuestion changes (non-null), send it as text
  useEffect(() => {
    if (selectedQuestion && connectionState === "connected") {
      sendText(selectedQuestion);
    }
  }, [selectedQuestion, connectionState, sendText]);

  const isConnected = connectionState === "connected";

  return (
    <div className="bg-gray-900 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="font-semibold">OpenAI Realtime Session</h2>
          <p className="text-xs text-gray-400">Direct browser→OpenAI WebRTC</p>
        </div>
        <div className="flex items-center gap-3">
          {ttsState === "playing" && (
            <span className="text-xs text-green-400 animate-pulse">🔊 Backend TTS</span>
          )}
          <div className={`w-2 h-2 rounded-full ${
            connectionState === "connected" ? "bg-green-500" :
            connectionState === "connecting" ? "bg-yellow-500 animate-pulse" :
            connectionState === "error" ? "bg-red-500" : "bg-gray-500"
          }`} />
          <span className="text-xs text-gray-400 capitalize">{connectionState}</span>
        </div>
      </div>

      {showFillerTradeoff && (
        <TradeoffPanel trigger="filler" onDismiss={() => setShowFillerTradeoff(false)} />
      )}

      {!isConnected ? (
        <div className="text-center py-8">
          <p className="text-gray-400 text-sm mb-4">
            Version B connects your browser directly to OpenAI Realtime via WebRTC.
            Math/history questions are dispatched to the backend orchestrator.
          </p>
          <button
            onClick={() => { connect(); setShowFillerTradeoff(true); }}
            disabled={connectionState === "connecting"}
            className="bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white rounded-lg py-2 px-6 font-medium transition-colors"
          >
            {connectionState === "connecting" ? "Connecting..." : "Start Session"}
          </button>
        </div>
      ) : (
        <div>
          {escalated && (
            <EscalationBanner
              version="b"
              onDismiss={() => setEscalated(false)}
            />
          )}
          <div className="flex items-center gap-2 mb-4 p-3 bg-green-900/20 border border-green-500/30 rounded-lg">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span className="text-sm text-green-300">Connected — speak your question</span>
            <button
              onClick={disconnect}
              className="ml-auto text-xs text-gray-400 hover:text-red-400 transition-colors"
            >
              Disconnect
            </button>
          </div>
          <TranscriptPanel turns={turns} />
        </div>
      )}
    </div>
  );
}
