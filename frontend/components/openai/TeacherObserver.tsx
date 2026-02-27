"use client";
import { useEffect, useRef, useState } from "react";
import type { TranscriptTurn } from "@/components/shared/TranscriptPanel";
import TranscriptPanel from "@/components/shared/TranscriptPanel";
import { useEscalationWatch } from "@/hooks/useEscalationWatch";

interface TeacherObserverProps {
  version: "a" | "b";
  sessionId: string;
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_B_URL ?? "http://localhost:8001";

export default function TeacherObserver({ version, sessionId }: TeacherObserverProps) {
  const [turns, setTurns] = useState<TranscriptTurn[]>([]);
  const [connected, setConnected] = useState(false);
  const [injection, setInjection] = useState("");
  const wsRef = useRef<WebSocket | null>(null);
  const escalation = useEscalationWatch(version === "b" ? sessionId : null);

  useEffect(() => {
    if (version !== "b" || !sessionId) return;

    const wsUrl = BACKEND_URL.replace("http://", "ws://").replace("https://", "wss://");
    const ws = new WebSocket(`${wsUrl}/ws/teacher/${sessionId}`);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = (e) => {
      console.error("Teacher WS error:", e);
      setConnected(false);
    };

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data as string) as {
          type: string;
          speaker?: string;
          text?: string;
          subject?: string;
        };
        if (data.type === "transcript") {
          setTurns((prev) => [...prev, {
            speaker: data.speaker ?? "unknown",
            text: data.text ?? "",
            subject: data.subject,
            timestamp: new Date(),
          }]);
        }
      } catch (e) { console.error("Teacher WS message parse error:", e); }
    };

    return () => ws.close();
  }, [version, sessionId]);

  const sendInjection = () => {
    if (!injection.trim() || !wsRef.current) return;
    wsRef.current.send(JSON.stringify({ type: "inject", text: injection }));
    setInjection("");
  };

  if (version === "a") {
    return (
      <div className="bg-gray-900 rounded-xl p-6">
        <p className="text-blue-400 font-medium mb-2">Version A — LiveKit Teacher Access</p>
        <p className="text-gray-300 text-sm">
          In Version A, you join the student&apos;s LiveKit room directly with full audio/video.
          The teacher token was generated and sent when the student escalated.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 rounded-xl p-6 space-y-4">
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${connected ? "bg-green-500" : "bg-gray-500"}`} />
        <span className="text-sm text-gray-400">{connected ? "Connected" : "Disconnected"}</span>
      </div>

      {escalation && (
        <div
          data-testid="escalation-panel"
          className="bg-yellow-900/50 border border-yellow-500/50 rounded-xl p-4"
        >
          <p className="font-semibold text-yellow-300 mb-1">Student escalated</p>
          <p className="text-sm text-gray-300">{escalation.reason ?? "Needs assistance"}</p>
          <p className="text-xs text-gray-500 mt-1">
            {new Date(escalation.created_at).toLocaleTimeString()}
          </p>
        </div>
      )}

      <TranscriptPanel turns={turns} />

      <div className="flex gap-2">
        <textarea
          data-testid="teacher-inject-input"
          value={injection}
          onChange={(e) => setInjection(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendInjection()}
          placeholder="Inject a hint or correction..."
          rows={2}
          className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-green-500 resize-none"
        />
        <button
          data-testid="teacher-inject-submit"
          onClick={sendInjection}
          disabled={!connected}
          className="bg-green-600 hover:bg-green-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
        >
          Inject
        </button>
      </div>
    </div>
  );
}
