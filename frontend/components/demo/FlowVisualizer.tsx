"use client";

interface Step {
  id: string;
  label: string;
  versionA: boolean;
  versionB: boolean;
}

const STEPS_A: Step[] = [
  { id: "stt", label: "STT", versionA: true, versionB: false },
  { id: "orchestrator", label: "Orchestrator (Haiku)", versionA: true, versionB: false },
  { id: "specialist", label: "Specialist LLM", versionA: true, versionB: true },
  { id: "guardrail", label: "Guardrail", versionA: true, versionB: true },
  { id: "tts", label: "TTS", versionA: true, versionB: true },
];

interface FlowVisualizerProps {
  version: "a" | "b";
  activeStep?: string;
}

export default function FlowVisualizer({ version, activeStep }: FlowVisualizerProps) {
  const steps = STEPS_A.filter((s) => (version === "a" ? s.versionA : s.versionB));

  return (
    <div className="mt-4 p-3 bg-gray-900 rounded-lg">
      <div className="text-xs text-gray-500 mb-2">Pipeline</div>
      <div className="flex items-center gap-2 overflow-x-auto">
        {steps.map((step, i) => (
          <div key={step.id} className="flex items-center gap-2">
            <div className={`px-2 py-1 rounded text-xs whitespace-nowrap ${
              activeStep === step.id
                ? "bg-yellow-500 text-black font-bold"
                : "bg-gray-800 text-gray-400"
            }`}>
              {step.label}
            </div>
            {i < steps.length - 1 && <span className="text-gray-600">→</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
