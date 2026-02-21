"use client";
import { useState } from "react";

export type TradeoffTrigger =
  | "english"
  | "guardrail"
  | "filler"
  | "teacher"
  | "barge-in";

interface TradeoffContent {
  title: string;
  versionA: string[];
  versionB: string[];
}

const TRADEOFFS: Record<TradeoffTrigger, TradeoffContent> = {
  english: {
    title: "English Question Routing",
    versionA: ["Separate Realtime AgentSession spins up", "~230ms TTFB", "Isolated from pipeline agents"],
    versionB: ["Realtime agent stays in control", "Calls dispatch_to_orchestrator tool", "No session switch overhead"],
  },
  guardrail: {
    title: "Content Safety Guardrail",
    versionA: ["Pre-TTS: GuardedAgent.tts_node", "Buffers at sentence boundaries", "Intercepts before synthesis"],
    versionB: ["Pre-TTS: backend /tts/stream", "Guardrail runs before streaming PCM", "tts_ready flag gates audio"],
  },
  filler: {
    title: "Filler While Thinking",
    versionA: ["Orchestrator speaks during routing", "Pipeline TTS (same voice)", "Continuous audio"],
    versionB: ["Realtime speaks filler phrases", "500ms → 1500ms → 3000ms thresholds", "Threshold counter (not string match)"],
  },
  teacher: {
    title: "Teacher Escalation",
    versionA: ["Teacher gets LiveKit JWT", "Joins WebRTC room", "Full audio + video + barge-in"],
    versionB: ["Teacher gets WebSocket URL", "Sees transcript only", "Can inject text responses"],
  },
  "barge-in": {
    title: "Barge-In / Interrupt",
    versionA: ["Pipeline flush", "Audio queue cleared", "VAD resumes immediately"],
    versionB: ["Realtime cancels response", "New turn_id issued", "Sub-100ms cancel"],
  },
};

interface TradeoffPanelProps {
  trigger: TradeoffTrigger;
  onDismiss?: () => void;
}

export default function TradeoffPanel({ trigger, onDismiss }: TradeoffPanelProps) {
  const content = TRADEOFFS[trigger];

  return (
    <div className="bg-gray-900 border border-yellow-500/50 rounded-xl p-4 my-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-yellow-400">⚡</span>
          <span className="font-semibold text-sm">How this works differently here</span>
        </div>
        {onDismiss && (
          <button onClick={onDismiss} className="text-gray-500 hover:text-gray-300 text-sm">✕</button>
        )}
      </div>
      <div className="text-xs text-gray-400 font-medium mb-2">{content.title}</div>
      <div className="grid grid-cols-2 gap-3 text-xs">
        <div>
          <div className="text-blue-400 font-medium mb-1">WITH LIVEKIT</div>
          <ul className="space-y-1">
            {content.versionA.map((item, i) => (
              <li key={i} className="text-gray-300">• {item}</li>
            ))}
          </ul>
        </div>
        <div>
          <div className="text-green-400 font-medium mb-1">WITHOUT LIVEKIT</div>
          <ul className="space-y-1">
            {content.versionB.map((item, i) => (
              <li key={i} className="text-gray-300">• {item}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
