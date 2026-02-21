"use client";
import { useEffect, useState } from "react";
import { useRoomContext } from "@livekit/components-react";

export interface TranscriptTurn {
  speaker: string;
  text: string;
  subject?: string;
  timestamp: Date;
}

export function useTranscript(): TranscriptTurn[] {
  const [turns, setTurns] = useState<TranscriptTurn[]>([]);
  const room = useRoomContext();

  useEffect(() => {
    if (!room) return;

    const handler = (payload: Uint8Array, participant: unknown, kind: unknown, topic?: string) => {
      if (topic !== "transcript") return;
      try {
        const text = new TextDecoder().decode(payload);
        const data = JSON.parse(text);
        setTurns((prev) => [
          ...prev,
          {
            speaker: data.speaker ?? "unknown",
            text: data.text ?? "",
            subject: data.subject,
            timestamp: new Date(),
          },
        ]);
      } catch {}
    };

    room.on("dataReceived", handler);
    return () => { room.off("dataReceived", handler); };
  }, [room]);

  return turns;
}
