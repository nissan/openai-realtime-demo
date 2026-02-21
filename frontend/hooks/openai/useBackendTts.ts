"use client";
import { useRef, useCallback, useState } from "react";

export type TtsState = "idle" | "loading" | "playing" | "error";

export interface BackendTtsHook {
  ttsState: TtsState;
  playJobAudio: (jobId: string, sessionId: string) => Promise<void>;
  stop: () => void;
}

export function useBackendTts(backendUrl: string): BackendTtsHook {
  const [ttsState, setTtsState] = useState<TtsState>("idle");
  const audioCtxRef = useRef<AudioContext | null>(null);
  const sourceRef = useRef<AudioBufferSourceNode | null>(null);

  const stop = useCallback(() => {
    sourceRef.current?.stop();
    sourceRef.current = null;
    setTtsState("idle");
  }, []);

  const playJobAudio = useCallback(async (jobId: string, sessionId: string) => {
    try {
      setTtsState("loading");

      if (!audioCtxRef.current) {
        audioCtxRef.current = new AudioContext({ sampleRate: 24000 });
      }
      const ctx = audioCtxRef.current;

      const res = await fetch(`${backendUrl}/tts/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: jobId, session_id: sessionId }),
      });

      if (!res.ok || !res.body) throw new Error("TTS stream failed");

      // Read chunked PCM and decode
      const reader = res.body.getReader();
      const chunks: Uint8Array[] = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        if (value) chunks.push(value);
      }

      const totalLength = chunks.reduce((sum, c) => sum + c.length, 0);
      const pcmData = new Uint8Array(totalLength);
      let offset = 0;
      for (const chunk of chunks) {
        pcmData.set(chunk, offset);
        offset += chunk.length;
      }

      // Convert PCM (16-bit signed, 24kHz) to AudioBuffer
      const samples = pcmData.length / 2;
      const audioBuffer = ctx.createBuffer(1, samples, 24000);
      const channelData = audioBuffer.getChannelData(0);
      const view = new DataView(pcmData.buffer);
      for (let i = 0; i < samples; i++) {
        channelData[i] = view.getInt16(i * 2, true) / 32768;
      }

      // Play with 50ms crossfade
      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(ctx.destination);

      const gainNode = ctx.createGain();
      gainNode.gain.setValueAtTime(0, ctx.currentTime);
      gainNode.gain.linearRampToValueAtTime(1, ctx.currentTime + 0.05); // 50ms fade in
      source.connect(gainNode);
      gainNode.connect(ctx.destination);

      sourceRef.current = source;
      setTtsState("playing");
      source.onended = () => setTtsState("idle");
      source.start();
    } catch (err) {
      console.error("Backend TTS failed:", err);
      setTtsState("error");
    }
  }, [backendUrl, stop]);

  return { ttsState, playJobAudio, stop };
}
