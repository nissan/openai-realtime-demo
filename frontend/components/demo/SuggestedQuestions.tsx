"use client";

interface Question {
  subject: "math" | "history" | "english";
  text: string;
}

const QUESTIONS: Question[] = [
  { subject: "math", text: "What is 25% of 80?" },
  { subject: "math", text: "Solve 2x² + 5x - 3 = 0" },
  { subject: "history", text: "Why did World War I start?" },
  { subject: "history", text: "What was the Roman Empire?" },
  { subject: "english", text: "Help me improve this sentence" },
  { subject: "english", text: "Explain what a metaphor is" },
];

const SUBJECT_COLORS = {
  math: "bg-blue-900/50 border-blue-500/30 text-blue-300",
  history: "bg-amber-900/50 border-amber-500/30 text-amber-300",
  english: "bg-purple-900/50 border-purple-500/30 text-purple-300",
};

interface SuggestedQuestionsProps {
  onSelect?: (question: string) => void;
}

export default function SuggestedQuestions({ onSelect }: SuggestedQuestionsProps) {
  return (
    <div className="bg-gray-900 rounded-xl p-4">
      <h3 className="text-sm font-semibold text-gray-400 mb-3">Try asking...</h3>
      <div className="space-y-2">
        {QUESTIONS.map((q, i) => (
          <button
            key={i}
            data-testid="suggested-question"
            onClick={() => onSelect?.(q.text)}
            className={`w-full text-left text-xs px-3 py-2 rounded-lg border transition-opacity hover:opacity-80 ${SUBJECT_COLORS[q.subject]}`}
          >
            <span className="font-medium capitalize mr-1">{q.subject}:</span>
            {q.text}
          </button>
        ))}
      </div>
    </div>
  );
}
