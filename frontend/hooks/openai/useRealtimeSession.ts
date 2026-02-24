"use client";
import { useEffect, useRef, useState, useCallback } from "react";

export type ConnectionState = "idle" | "connecting" | "connected" | "error";

export interface RealtimeSessionOptions {
  onTranscript?: (speaker: "user" | "assistant", text: string) => void;
  onToolCall?: (name: string, args: Record<string, unknown>) => void;
}

export interface RealtimeSessionHook {
  connectionState: ConnectionState;
  connect: () => Promise<void>;
  disconnect: () => void;
  sendText: (text: string) => void;
}

export function useRealtimeSession(
  backendUrl: string,
  sessionId: string,
  options?: RealtimeSessionOptions
): RealtimeSessionHook {
  const [connectionState, setConnectionState] = useState<ConnectionState>("idle");
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const dcRef = useRef<RTCDataChannel | null>(null);
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const disconnect = useCallback(() => {
    dcRef.current?.close();
    pcRef.current?.close();
    pcRef.current = null;
    dcRef.current = null;
    setConnectionState("idle");
  }, []);

  const connect = useCallback(async () => {
    try {
      setConnectionState("connecting");

      // Get ephemeral key from backend, pass session_id so backend can log it
      const tokenRes = await fetch(
        `${backendUrl}/session/token?session_id=${encodeURIComponent(sessionId)}`,
        { method: "POST" }
      );
      if (!tokenRes.ok) throw new Error("Failed to get session token");
      const { client_secret } = await tokenRes.json();

      // Create WebRTC peer connection
      const pc = new RTCPeerConnection();
      pcRef.current = pc;

      // Add microphone track
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((track) => pc.addTrack(track, stream));

      // Remote audio output
      const audioEl = new Audio();
      audioEl.autoplay = true;
      pc.ontrack = (e) => { audioEl.srcObject = e.streams[0]; };

      // Data channel for events
      const dc = pc.createDataChannel("oai-events");
      dcRef.current = dc;

      dc.onopen = () => {
        setConnectionState("connected");
      };

      dc.onmessage = (e) => {
        try {
          const event = JSON.parse(e.data as string);
          const opts = optionsRef.current;

          if (
            event.type === "conversation.item.input_audio_transcription.completed" &&
            opts?.onTranscript
          ) {
            opts.onTranscript("user", event.transcript ?? "");
          } else if (
            event.type === "response.audio_transcript.done" &&
            opts?.onTranscript
          ) {
            opts.onTranscript("assistant", event.transcript ?? "");
          } else if (
            event.type === "response.output_item.done" &&
            event.item?.type === "function_call" &&
            opts?.onToolCall
          ) {
            try {
              const args = JSON.parse(event.item.arguments ?? "{}") as Record<string, unknown>;
              opts.onToolCall(event.item.name as string, args);
            } catch (parseErr) {
              console.error("Failed to parse tool call arguments:", parseErr);
            }
          }
        } catch (err) {
          console.error("dc.onmessage parse error:", err);
        }
      };

      // Create SDP offer
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      // Connect to OpenAI Realtime
      const sdpRes = await fetch(
        "https://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview",
        {
          method: "POST",
          body: offer.sdp,
          headers: {
            Authorization: `Bearer ${client_secret.value}`,
            "Content-Type": "application/sdp",
          },
        }
      );

      const answerSdp = await sdpRes.text();
      await pc.setRemoteDescription({ type: "answer", sdp: answerSdp });

    } catch (err) {
      console.error("Realtime connection failed:", err);
      setConnectionState("error");
      disconnect();
    }
  }, [backendUrl, sessionId, disconnect]);

  const sendText = useCallback((text: string) => {
    if (dcRef.current?.readyState === "open") {
      dcRef.current.send(JSON.stringify({
        type: "conversation.item.create",
        item: { type: "message", role: "user", content: [{ type: "input_text", text }] },
      }));
      dcRef.current.send(JSON.stringify({ type: "response.create" }));
    }
  }, []);

  useEffect(() => () => disconnect(), [disconnect]);

  return { connectionState, connect, disconnect, sendText };
}
