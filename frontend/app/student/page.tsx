"use client";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import StudentRoom from "@/components/livekit/StudentRoom";
import RealtimeSession from "@/components/openai/RealtimeSession";
import SuggestedQuestions from "@/components/demo/SuggestedQuestions";
import FlowVisualizer from "@/components/demo/FlowVisualizer";
import TranscriptPanel from "@/components/shared/TranscriptPanel";
import TradeoffPanel, { TradeoffTrigger } from "@/components/demo/TradeoffPanel";

const VALID_TRIGGERS: TradeoffTrigger[] = ["english", "guardrail", "filler", "teacher", "barge-in"];

function StudentPageContent() {
  const searchParams = useSearchParams();
  const version = searchParams.get("v") === "b" ? "b" : "a";
  const tradeoffParam = searchParams.get("tradeoff");
  const tradeoff = VALID_TRIGGERS.includes(tradeoffParam as TradeoffTrigger)
    ? (tradeoffParam as TradeoffTrigger)
    : null;
  const [showTradeoff, setShowTradeoff] = useState(true);
  const [selectedQuestion, setSelectedQuestion] = useState<string | null>(null);
  const [activeStep, setActiveStep] = useState<string | undefined>(undefined);

  const handleSelectQuestion = (q: string) => {
    setSelectedQuestion(q);
    // Clear after a tick so the effect fires each time the same question is selected
    setTimeout(() => setSelectedQuestion(null), 100);
  };

  return (
    <main className="container mx-auto px-4 py-8">
      <div className="mb-6 flex items-center gap-3">
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${
          version === "a"
            ? "bg-blue-600 text-white"
            : "bg-green-600 text-white"
        }`}>
          {version === "a" ? "Version A — LiveKit" : "Version B — OpenAI Realtime"}
        </span>
        <a href="/" className="text-gray-400 hover:text-white text-sm">← Change version</a>
      </div>

      {tradeoff && showTradeoff && (
        <TradeoffPanel trigger={tradeoff} onDismiss={() => setShowTradeoff(false)} />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          {version === "a" ? (
            <StudentRoom
              selectedQuestion={selectedQuestion}
              onPipelineStep={(step) => setActiveStep(step ?? undefined)}
            />
          ) : (
            <RealtimeSession
              selectedQuestion={selectedQuestion}
              onPipelineStep={(step) => setActiveStep(step ?? undefined)}
            />
          )}
          <FlowVisualizer version={version} activeStep={activeStep} />
        </div>
        <div className="space-y-4">
          <SuggestedQuestions onSelect={handleSelectQuestion} />
          <TranscriptPanel />
        </div>
      </div>
    </main>
  );
}

export default function StudentPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Loading...</div>}>
      <StudentPageContent />
    </Suspense>
  );
}
