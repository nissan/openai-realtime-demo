"use client";
import { useEffect, useRef, useState, useCallback } from "react";

export type ConnectionState = "idle" | "connecting" | "connected" | "error";

export interface RealtimeSessionHook {
  connectionState: ConnectionState;
  connect: () => Promise<void>;
  disconnect: () => void;
  sendText: (text: string) => void;
}

export function useRealtimeSession(backendUrl: string): RealtimeSessionHook {
  const [connectionState, setConnectionState] = useState<ConnectionState>("idle");
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const dcRef = useRef<RTCDataChannel | null>(null);

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

      // Get ephemeral key from backend
      const tokenRes = await fetch(`${backendUrl}/session/token`, { method: "POST" });
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

      setConnectionState("connected");
    } catch (err) {
      console.error("Realtime connection failed:", err);
      setConnectionState("error");
      disconnect();
    }
  }, [backendUrl, disconnect]);

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
