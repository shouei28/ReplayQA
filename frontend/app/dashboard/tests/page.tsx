"use client";

import { useState, useEffect, useCallback } from "react";
import TestList from "@/components/dashboard/TestList";
import TestHistoryList from "@/components/dashboard/TestHistoryList";
import TestDetailModal from "@/components/dashboard/TestDetailModal";
import DefineTestModal from "@/components/dashboard/DefineTestModal";
import { testsApi, pipelineApi, executionsApi } from "@/lib/api";
import type { Test, TestExecution } from "@/lib/types";
import { useToast } from "@/hooks/use-toast";

export default function TestsPage() {
  const [tests, setTests] = useState<Test[]>([]);
  const [executions, setExecutions] = useState<TestExecution[]>([]);
  const [loadingTests, setLoadingTests] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [selectedTest, setSelectedTest] = useState<Test | null>(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [defineModalOpen, setDefineModalOpen] = useState(false);
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

  const fetchHistory = useCallback(async (showLoading = true) => {
    if (showLoading) setLoadingHistory(true);
    try {
      const data = await executionsApi.list();
      setExecutions(data.results ?? []);
    } catch {
      if (showLoading) setExecutions([]);
    } finally {
      if (showLoading) setLoadingHistory(false);
    }
  }, []);

  useEffect(() => {
    fetchTests();
    fetchHistory();
  }, [fetchTests, fetchHistory]);

  /* ---- Poll when any execution is running --------------------------------- */
  const hasRunning = executions.some(
    (e) => e.status === "running" || e.status === "pending"
  );
  useEffect(() => {
    if (!hasRunning) return;
    const interval = setInterval(() => {
      fetchHistory(false); // silent refresh, no loading state
    }, 3000);
    return () => clearInterval(interval);
  }, [hasRunning, fetchHistory]);

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
      // Optimistic update: add new execution to list immediately
      const now = new Date().toISOString();
      const newExecution: TestExecution = {
        id: res.job_id,
        test_id: test.id,
        test_name: test.test_name,
        description: test.description,
        url: test.url,
        steps: test.steps,
        expected_behavior: test.expected_behavior,
        status: "pending",
        progress: 0,
        message: null,
        total_runtime_sec: null,
        started_at: null,
        completed_at: null,
        browserbase_session_id: null,
        error_message: null,
        created_at: now,
        updated_at: now,
      };
      setExecutions((prev) => [newExecution, ...prev]);
      // Refresh from server in background (don't await — optimistic update shows immediately)
      void fetchHistory(false);
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

  async function handleDeleteExecution(executionId: string) {
    if (!confirm("Delete this test execution from history?")) return;
    try {
      await executionsApi.delete(executionId);
      setExecutions((prev) => prev.filter((e) => e.id !== executionId));
      toast({ title: "Execution deleted" });
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

  function handleTestClick(test: Test) {
    setSelectedTest(test);
    setDetailModalOpen(true);
  }

  async function handleSaveTest(testId: string, updates: Partial<Test>) {
    await testsApi.update(testId, updates);
    setTests((prev) =>
      prev.map((t) => (t.id === testId ? { ...t, ...updates } : t))
    );
    toast({ title: "Test updated" });
  }

  async function handleCreateTest(data: Omit<Test, "id" | "created_at" | "updated_at">) {
    const created = await testsApi.create(data);
    setTests((prev) => [created, ...prev]);
    toast({ title: "Test created" });
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
            onTestClick={handleTestClick}
            onDefineNew={() => setDefineModalOpen(true)}
          />

          <DefineTestModal
            open={defineModalOpen}
            onClose={() => setDefineModalOpen(false)}
            onCreate={handleCreateTest}
          />

          <TestDetailModal
            test={selectedTest}
            open={detailModalOpen}
            onClose={() => {
              setDetailModalOpen(false);
              setSelectedTest(null);
            }}
            onSave={handleSaveTest}
          />

          <TestHistoryList
            executions={executions}
            loading={loadingHistory}
            onDelete={handleDeleteExecution}
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
