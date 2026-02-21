"use client";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import TeacherObserver from "@/components/openai/TeacherObserver";

function TeacherPageContent() {
  const searchParams = useSearchParams();
  const version = searchParams.get("v") === "b" ? "b" : "a";
  const sessionId = searchParams.get("session") ?? "";

  return (
    <main className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Teacher Portal</h1>
        <p className="text-gray-400">
          {version === "a"
            ? "Version A: Join the LiveKit room to observe with full audio/video"
            : "Version B: Monitor transcript and inject guidance via WebSocket"}
        </p>
      </div>
      <TeacherObserver version={version} sessionId={sessionId} />
    </main>
  );
}

export default function TeacherPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Loading...</div>}>
      <TeacherPageContent />
    </Suspense>
  );
}
