import VersionSelector from "@/components/landing/VersionSelector";
import ArchitectureCompare from "@/components/landing/ArchitectureCompare";

export default function HomePage() {
  return (
    <main className="container mx-auto px-4 py-12">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">Voice AI Tutor</h1>
        <p className="text-xl text-gray-400 max-w-2xl mx-auto">
          Compare two architectures for voice AI tutoring. Choose a version to demo.
        </p>
      </div>
      <VersionSelector />
      <ArchitectureCompare />
    </main>
  );
}
