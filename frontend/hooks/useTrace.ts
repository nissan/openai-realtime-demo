"use client";
import { useCallback } from "react";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_B_URL ?? "http://localhost:8001";

export function useTrace(sessionId: string) {
  const trace = useCallback((
    eventName: string,
    attributes?: Record<string, string | number | boolean>,
  ) => {
    fetch(`${BACKEND_URL}/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, event_name: eventName, attributes: attributes ?? {} }),
    }).catch(() => {}); // Observability must never break the app
  }, [sessionId]);

  return { trace };
}
