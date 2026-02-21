"use client";
import { useState } from "react";

const rows = [
  { label: "Latency (TTFB)", a: "~230ms (pipeline)", b: "~120ms (direct WebRTC)" },
  { label: "Safety / Guardrail", a: "Pre-TTS in GuardedAgent.tts_node", b: "Pre-TTS in /tts/stream" },
  { label: "English subject", a: "Separate Realtime AgentSession", b: "Same Realtime session" },
  { label: "Teacher escalation", a: "LiveKit JWT → audio/video room", b: "WebSocket → transcript only" },
  { label: "Barge-in", a: "Pipeline flush + VAD resume", b: "Realtime response cancel" },
  { label: "Filler audio", a: "Orchestrator speaks during routing", b: "500ms / 1500ms / 3000ms thresholds" },
  { label: "Infrastructure", a: "19 services (incl. LiveKit)", b: "16 services (no LiveKit)" },
];

export default function ArchitectureCompare() {
  const [open, setOpen] = useState(false);

  return (
    <div className="border border-gray-700 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-900 transition-colors"
      >
        <span className="font-semibold">Architecture Comparison</span>
        <span className="text-gray-400">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-900">
              <tr>
                <th className="px-4 py-2 text-left text-gray-400">Feature</th>
                <th className="px-4 py-2 text-left text-blue-400">Version A — LiveKit</th>
                <th className="px-4 py-2 text-left text-green-400">Version B — OpenAI Realtime</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i} className="border-t border-gray-800">
                  <td className="px-4 py-3 font-medium text-gray-300">{row.label}</td>
                  <td className="px-4 py-3 text-gray-400">{row.a}</td>
                  <td className="px-4 py-3 text-gray-400">{row.b}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
