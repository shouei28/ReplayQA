import { Recorder } from "@/components/recorder";

export default function RecorderPage() {
  return (
    <main className="min-h-screen bg-zinc-100 p-6">
      <div className="mx-auto max-w-7xl">
        <h1 className="mb-4 text-2xl font-semibold text-zinc-800">
          Recorder
        </h1>
        <p className="mb-6 text-sm text-zinc-500">
          Enter a URL, start recording, then interact in the browser. Your actions are captured as steps. End the session to save the test.
        </p>
        <Recorder />
      </div>
    </main>
  );
}
