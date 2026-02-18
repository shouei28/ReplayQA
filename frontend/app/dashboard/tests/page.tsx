"use client";

import { useState, useEffect, useCallback } from "react";
import TestList from "@/components/dashboard/TestList";
import TestHistoryList from "@/components/dashboard/TestHistoryList";
import { testsApi, pipelineApi, executionsApi } from "@/lib/api";
import type { Test, TestExecution } from "@/lib/types";
import { useToast } from "@/hooks/use-toast";

export default function TestsPage() {
  const [tests, setTests] = useState<Test[]>([]);
  const [executions, setExecutions] = useState<TestExecution[]>([]);
  const [loadingTests, setLoadingTests] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const { toast } = useToast();

  /* ---- Fetch data ---------------------------------------------------- */

  const fetchTests = useCallback(async () => {
    setLoadingTests(true);
    try {
      const data = await testsApi.list();
      setTests(Array.isArray(data) ? data : []);
    } catch {
      // API not available — use empty state
      setTests([]);
    } finally {
      setLoadingTests(false);
    }
  }, []);

  const fetchHistory = useCallback(async () => {
    setLoadingHistory(true);
    try {
      const data = await executionsApi.list();
      setExecutions(data.results ?? []);
    } catch {
      setExecutions([]);
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  useEffect(() => {
    fetchTests();
    fetchHistory();
  }, [fetchTests, fetchHistory]);

  /* ---- Handlers ------------------------------------------------------ */

  async function handleRun(test: Test) {
    try {
      const res = await pipelineApi.run({
        url: test.url,
        description: test.description,
        steps: test.steps,
        expected_behavior: test.expected_behavior,
        test_id: test.id,
        test_name: test.test_name,
      });
      toast({
        title: "Test started",
        description: `Pipeline queued (${res.job_id.slice(0, 8)}…)`,
      });
      // Refresh history to show the new pending execution
      fetchHistory();
    } catch (err) {
      toast({
        title: "Failed to start test",
        description: String(err),
        variant: "destructive",
      });
    }
  }

  async function handleDelete(test: Test) {
    if (!confirm(`Delete "${test.test_name}"?`)) return;
    try {
      await testsApi.delete(test.id);
      setTests((prev) => prev.filter((t) => t.id !== test.id));
      toast({ title: "Test deleted" });
    } catch (err) {
      toast({
        title: "Delete failed",
        description: String(err),
        variant: "destructive",
      });
    }
  }

  async function handleRunSelected(ids: string[]) {
    const selected = tests.filter((t) => ids.includes(t.id));
    for (const test of selected) {
      await handleRun(test);
    }
  }

  /* ---- Tabs ---------------------------------------------------------- */

  const [tab, setTab] = useState<"tests" | "scheduled">("tests");

  return (
    <div className="max-w-6xl">
      {/* Tab bar */}
      <div className="flex items-center gap-1 mb-6 border-b border-gray-200">
        <button
          onClick={() => setTab("tests")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === "tests"
              ? "border-gray-900 text-gray-900"
              : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
        >
          Tests
        </button>
        <button
          onClick={() => setTab("scheduled")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === "scheduled"
              ? "border-gray-900 text-gray-900"
              : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
        >
          Scheduled
        </button>
      </div>

      {tab === "tests" && (
        <>
          <TestList
            tests={tests}
            loading={loadingTests}
            onRun={handleRun}
            onDelete={handleDelete}
            onRunSelected={handleRunSelected}
          />

          <TestHistoryList
            executions={executions}
            loading={loadingHistory}
          />
        </>
      )}

      {tab === "scheduled" && (
        <div className="text-center py-16 text-gray-400">
          <p className="text-lg">Scheduled tests coming soon</p>
          <p className="text-sm mt-1">
            Set up recurring test runs on a schedule.
          </p>
        </div>
      )}
    </div>
  );
}
