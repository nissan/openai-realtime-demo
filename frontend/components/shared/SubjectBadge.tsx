const BADGES: Record<string, { label: string; className: string }> = {
  math: { label: "Math", className: "bg-cyan-900/50 text-cyan-300 border border-cyan-500/30" },
  history: { label: "History", className: "bg-amber-900/50 text-amber-300 border border-amber-500/30" },
  english: { label: "English", className: "bg-purple-900/50 text-purple-300 border border-purple-500/30" },
};

export default function SubjectBadge({ subject }: { subject: string }) {
  const badge = BADGES[subject] ?? { label: subject, className: "bg-gray-800 text-gray-400" };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${badge.className}`}>
      {badge.label}
    </span>
  );
}
