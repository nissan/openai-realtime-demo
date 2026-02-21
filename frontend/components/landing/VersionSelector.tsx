import Link from "next/link";

export default function VersionSelector() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
      <div className="bg-gray-900 border border-blue-500/30 rounded-xl p-6 hover:border-blue-500 transition-colors">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-2xl">🔗</span>
          <h2 className="text-xl font-bold text-blue-400">Version A — LiveKit</h2>
        </div>
        <ul className="space-y-2 text-sm text-gray-300 mb-6">
          <li>✓ Multi-participant WebRTC rooms</li>
          <li>✓ Pipeline STT → LLM → TTS with GuardedAgent</li>
          <li>✓ Native barge-in and VAD</li>
          <li>✓ Teacher joins room with full audio/video</li>
          <li>✓ OpenAI Realtime only for English specialist</li>
        </ul>
        <div className="text-xs text-gray-500 mb-4">Infrastructure: 19 services</div>
        <Link
          href="/student?v=a"
          className="block w-full text-center bg-blue-600 hover:bg-blue-500 text-white rounded-lg py-2 px-4 font-medium transition-colors"
        >
          Start Demo →
        </Link>
      </div>

      <div className="bg-gray-900 border border-green-500/30 rounded-xl p-6 hover:border-green-500 transition-colors">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-2xl">⚡</span>
          <h2 className="text-xl font-bold text-green-400">Version B — OpenAI Realtime Direct</h2>
        </div>
        <ul className="space-y-2 text-sm text-gray-300 mb-6">
          <li>✓ Browser WebRTC directly to OpenAI</li>
          <li>✓ Minimal infrastructure, fast setup</li>
          <li>✓ Backend TTS streaming for guardrailed answers</li>
          <li>✓ Filler phrases at 500ms/1500ms/3000ms</li>
          <li>✓ Teacher observes via WebSocket</li>
        </ul>
        <div className="text-xs text-gray-500 mb-4">Infrastructure: 16 services</div>
        <Link
          href="/student?v=b"
          className="block w-full text-center bg-green-600 hover:bg-green-500 text-white rounded-lg py-2 px-4 font-medium transition-colors"
        >
          Start Demo →
        </Link>
      </div>
    </div>
  );
}
