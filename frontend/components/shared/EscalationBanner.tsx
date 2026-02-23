"use client";

interface EscalationBannerProps {
  version: "a" | "b";
  teacherToken?: string;
  teacherWsUrl?: string;
  onDismiss?: () => void;
}

export default function EscalationBanner({ version, teacherToken, teacherWsUrl, onDismiss }: EscalationBannerProps) {
  return (
    <div data-testid="escalation-banner" className="bg-yellow-900/50 border border-yellow-500/50 rounded-xl p-4 mb-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="font-semibold text-yellow-300 mb-1">👩‍🏫 Teacher Notified</p>
          <p className="text-sm text-gray-300">
            {version === "a"
              ? "A teacher has been invited to join your LiveKit room with audio and video."
              : "A teacher is monitoring your session via WebSocket and may send guidance."}
          </p>
          {version === "a" && teacherToken && (
            <p className="text-xs text-gray-500 mt-1 font-mono truncate">JWT: {teacherToken.slice(0, 40)}...</p>
          )}
          {version === "b" && teacherWsUrl && (
            <p className="text-xs text-gray-500 mt-1 font-mono">{teacherWsUrl}</p>
          )}
        </div>
        {onDismiss && (
          <button onClick={onDismiss} className="text-gray-500 hover:text-gray-300">✕</button>
        )}
      </div>
    </div>
  );
}
