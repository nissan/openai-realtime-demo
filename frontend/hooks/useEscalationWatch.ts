"use client";
import { useEffect, useState } from "react";
import { createClient } from "@supabase/supabase-js";

interface EscalationEvent {
  session_id: string;
  reason: string | null;
  teacher_ws_url: string | null;
  created_at: string;
}

export function useEscalationWatch(sessionId: string | null): EscalationEvent | null {
  const [event, setEvent] = useState<EscalationEvent | null>(null);

  useEffect(() => {
    const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    if (!sessionId || !url || !key) return;

    const supabase = createClient(url, key);
    const channel = supabase
      .channel(`escalation:${sessionId}`)
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "escalation_events",
          filter: `session_id=eq.${sessionId}`,
        },
        (payload) => setEvent(payload.new as EscalationEvent)
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [sessionId]);

  return event;
}
