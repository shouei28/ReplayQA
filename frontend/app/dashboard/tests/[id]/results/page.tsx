"use client";

import { useState, useEffect, useCallback, use } from "react";
import Link from "next/link";
import { pipelineApi } from "@/lib/api";
import type { TestExecution, TestResult } from "@/lib/types";
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  ExternalLink,
  Image as ImageIcon,
} from "lucide-react";

export default function TestResultsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [execution, setExecution] = useState<TestExecution | null>(null);
  const [result, setResult] = useState<TestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [liveViewUrl, setLiveViewUrl] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const exec = await pipelineApi.status(id);
      setExecution(exec);

      if (exec.status === "completed" || exec.status === "failed") {
        setLiveViewUrl(null); // Clear live view when done
        try {
          const res = await pipelineApi.results(id);
          setResult(res);
        } catch {
          // Results may not exist for failed executions
        }
      }

      // Fetch live view URL when running
      if (exec.status === "running" && !liveViewUrl) {
        try {
          const lv = await pipelineApi.liveView(id);
          if (lv.live_view_url) {
            setLiveViewUrl(lv.live_view_url);
          }
        } catch {
          // Live view may not be available yet (session still creating)
        }
      }
    } catch (err) {
      setError(String(err));
    }
  }, [id, liveViewUrl]);

  useEffect(() => {
    fetchData();
    // Poll while running
    const interval = setInterval(() => {
      if (execution?.status === "running" || execution?.status === "pending") {
        fetchData();
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [fetchData, execution?.status]);

  if (error) {
    return (
      <div className="max-w-4xl">
        <BackLink />
        <div className="mt-6 p-6 bg-red-50 border border-red-200 rounded-xl text-red-700">
          {error}
        </div>
      </div>
    );
  }

  if (!execution) {
    return (
      <div className="max-w-4xl">
        <BackLink />
        <div className="mt-6 animate-pulse space-y-4">
          <div className="h-8 w-64 bg-gray-100 rounded" />
          <div className="h-4 w-96 bg-gray-100 rounded" />
          <div className="h-48 bg-gray-100 rounded-xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl">
      <BackLink />

      {/* Header */}
      <div className="mt-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {execution.test_name}
          </h1>
          <p className="text-sm text-gray-500 mt-1">{execution.description}</p>
          <div className="flex items-center gap-3 mt-3">
            <StatusBadge status={execution.status} />
            <a
              href={execution.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-indigo-600 transition-colors"
            >
              <ExternalLink size={12} />
              {execution.url}
            </a>
          </div>
        </div>

        {execution.total_runtime_sec != null && (
          <div className="text-right">
            <p className="text-2xl font-bold text-gray-900">
              {execution.total_runtime_sec.toFixed(1)}s
            </p>
            <p className="text-xs text-gray-400">total runtime</p>
          </div>
        )}
      </div>

      {/* Progress bar for running tests */}
      {(execution.status === "running" || execution.status === "pending") && (
        <div className="mt-6">
          <div className="flex items-center justify-between text-sm mb-2">
            <span className="text-gray-600">{execution.message || "Waiting…"}</span>
            <span className="text-gray-500 font-mono">{execution.progress}%</span>
          </div>
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-500"
              style={{ width: `${execution.progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Live View iframe */}
      {liveViewUrl && (execution.status === "running" || execution.status === "pending") && (
        <div className="mt-6">
          <div className="flex items-center gap-2 mb-3">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500" />
            </span>
            <h2 className="text-sm font-semibold text-gray-900">Live Browser View</h2>
          </div>
          <div className="border border-gray-200 rounded-xl overflow-hidden shadow-sm">
            <iframe
              src={liveViewUrl}
              className="w-full bg-gray-900"
              style={{ height: "500px" }}
              allow="clipboard-read; clipboard-write"
              title="Live browser view"
            />
          </div>
        </div>
      )}

      {/* Error message */}
      {execution.status === "failed" && execution.error_message && (
        <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-xl">
          <p className="text-sm font-medium text-red-800">Execution Error</p>
          <p className="text-sm text-red-600 mt-1 font-mono">
            {execution.error_message}
          </p>
        </div>
      )}

      {/* Results */}
      {result && (
        <>
          {/* Summary card */}
          <div className="mt-8 grid grid-cols-3 gap-4">
            <SummaryCard
              label="Result"
              value={result.success ? "PASS" : "FAIL"}
              color={result.success ? "emerald" : "red"}
            />
            <SummaryCard
              label="Steps Passed"
              value={`${result.passed_steps}/${result.total_steps}`}
              color="gray"
            />
            <SummaryCard
              label="Tokens Used"
              value={result.total_tokens.toLocaleString()}
              color="gray"
            />
          </div>

          {/* Agent execution log */}
          <div className="mt-8">
            <h2 className="text-lg font-bold text-gray-900 mb-1">
              Agent Execution Log
            </h2>
            <p className="text-xs text-gray-500 mb-4">
              Individual actions the AI agent performed to complete your test steps.
            </p>
            <div className="space-y-3">
              {result.executed_steps.map((step, i) => (
                <div
                  key={i}
                  className="flex items-start gap-3 p-4 border border-gray-200 rounded-xl bg-white"
                >
                  <div className="mt-0.5">
                    {step.status === "passed" ? (
                      <CheckCircle2
                        size={18}
                        className="text-emerald-500"
                      />
                    ) : (
                      <XCircle size={18} className="text-red-500" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">
                      Turn {i + 1}: {step.instruction || step.type}
                    </p>
                    {step.error && (
                      <p className="text-xs text-red-500 mt-1 font-mono">
                        {step.error}
                      </p>
                    )}
                  </div>
                  {step.screenshot_url && (
                    <a
                      href={step.screenshot_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-xs text-gray-400 hover:text-indigo-600 transition-colors"
                    >
                      <ImageIcon size={14} />
                      Screenshot
                    </a>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* AI Explanation */}
          {result.explanation && (
            <div className="mt-8">
              <h2 className="text-lg font-bold text-gray-900 mb-3">
                AI Analysis
              </h2>
              <div className="p-5 bg-gray-50 border border-gray-200 rounded-xl">
                <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans leading-relaxed">
                  {result.explanation}
                </pre>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* -------------------------------------------------------------------- */
/*  Sub-components                                                       */
/* -------------------------------------------------------------------- */

function BackLink() {
  return (
    <Link
      href="/dashboard/tests"
      className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900 transition-colors"
    >
      <ArrowLeft size={16} />
      Back to Tests
    </Link>
  );
}

function StatusBadge({ status }: { status: TestExecution["status"] }) {
  const styles: Record<string, string> = {
    completed: "bg-emerald-50 text-emerald-700",
    failed: "bg-red-50 text-red-700",
    running: "bg-blue-50 text-blue-700",
    pending: "bg-gray-100 text-gray-500",
  };
  const icons: Record<string, React.ReactNode> = {
    completed: <CheckCircle2 size={14} />,
    failed: <XCircle size={14} />,
    running: <Loader2 size={14} className="animate-spin" />,
    pending: <Clock size={14} />,
  };
  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${styles[status] || styles.pending}`}
    >
      {icons[status]}
      {status}
    </span>
  );
}

function SummaryCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  const colorMap: Record<string, string> = {
    emerald: "text-emerald-700 bg-emerald-50 border-emerald-200",
    red: "text-red-700 bg-red-50 border-red-200",
    gray: "text-gray-700 bg-white border-gray-200",
  };
  return (
    <div className={`p-4 rounded-xl border ${colorMap[color] || colorMap.gray}`}>
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
    </div>
  );
}
