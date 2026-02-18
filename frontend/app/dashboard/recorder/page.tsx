"use client";

import { Recorder } from "@/components/recorder";

export default function DashboardRecorderPage() {
    return (
        <div className="max-w-7xl">
            <h1 className="mb-2 text-2xl font-bold text-zinc-900">
                Recorder
            </h1>
            <p className="mb-6 text-sm text-zinc-500">
                Enter a URL, start recording, then interact in the browser. Your
                actions are captured as steps. End the session to save the test.
            </p>
            <Recorder />
        </div>
    );
}
