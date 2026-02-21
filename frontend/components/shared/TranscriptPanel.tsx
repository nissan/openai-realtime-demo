"use client";
import { useRef, useEffect } from "react";

export interface TranscriptTurn {
  speaker: string;
  text: string;
  subject?: string;
  timestamp?: Date;
}

const SPEAKER_COLORS: Record<string, string> = {
  student: "text-white",
  orchestrator: "text-blue-400",
  math: "text-cyan-400",
  history: "text-amber-400",
  english: "text-purple-400",
  teacher: "text-green-400",
};

interface TranscriptPanelProps {
  turns?: TranscriptTurn[];
}

export default function TranscriptPanel({ turns = [] }: TranscriptPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns.length]);

  return (
    <div className="bg-gray-900 rounded-xl p-4">
      <h3 className="text-sm font-semibold text-gray-400 mb-3">Transcript</h3>
      <div className="space-y-2 max-h-64 overflow-y-auto text-sm">
        {turns.length === 0 && (
          <p className="text-gray-600 text-xs italic">Conversation will appear here...</p>
        )}
        {turns.map((turn, i) => (
          <div key={i} className="flex gap-2">
            <span className={`font-medium shrink-0 capitalize ${SPEAKER_COLORS[turn.speaker] ?? "text-gray-400"}`}>
              {turn.speaker}:
            </span>
            <span className="text-gray-300">{turn.text}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
