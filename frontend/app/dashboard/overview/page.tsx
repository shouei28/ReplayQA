"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { testsApi, executionsApi } from "@/lib/api";
import type { Test, TestExecution } from "@/lib/types";
import {
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  Plus,
  Play,
  ArrowRight,
} from "lucide-react";

export default function DashboardOverviewPage() {
  const [tests, setTests] = useState<Test[]>([]);
  const [executions, setExecutions] = useState<TestExecution[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [testData, execData] = await Promise.all([
          testsApi.list(),
          executionsApi.list(),
        ]);
        setTests(Array.isArray(testData) ? testData : []);
        setExecutions(execData.results ?? []);
      } catch {
        // API not available
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const completed = executions.filter((e) => e.status === "completed");
  const failed = executions.filter((e) => e.status === "failed");
  const running = executions.filter((e) => e.status === "running");
  const recent = executions.slice(0, 5);

  if (loading) {
    return (
      <div className="max-w-6xl animate-pulse space-y-6">
        <div className="h-8 w-48 bg-zinc-100 rounded" />
        <div className="grid grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="h-24 bg-zinc-100 rounded-xl"
            />
          ))}
        </div>
        <div className="h-64 bg-zinc-100 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl">
      <h1 className="text-2xl font-bold text-zinc-900 mb-6">Overview</h1>

      {/* Stats grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Saved Tests"
          value={tests.length}
          icon={
            <div className="w-9 h-9 rounded-lg bg-indigo-50 flex items-center justify-center">
              <Plus size={18} className="text-indigo-600" />
            </div>
          }
        />
        <StatCard
          label="Total Runs"
          value={executions.length}
          icon={
            <div className="w-9 h-9 rounded-lg bg-zinc-100 flex items-center justify-center">
              <Play size={18} className="text-zinc-600" />
            </div>
          }
        />
        <StatCard
          label="Passed"
          value={completed.length}
          icon={
            <div className="w-9 h-9 rounded-lg bg-emerald-50 flex items-center justify-center">
              <CheckCircle2
                size={18}
                className="text-emerald-600"
              />
            </div>
          }
        />
        <StatCard
          label="Failed"
          value={failed.length}
          icon={
            <div className="w-9 h-9 rounded-lg bg-red-50 flex items-center justify-center">
              <XCircle size={18} className="text-red-500" />
            </div>
          }
        />
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <QuickAction
          href="/dashboard/recorder"
          title="Record a Test"
          description="Open a browser session and record your actions"
          color="indigo"
        />
        <QuickAction
          href="/dashboard/tests"
          title="View Tests"
          description="Manage and run your saved test definitions"
          color="zinc"
        />
        <QuickAction
          href="/dashboard/activity"
          title="Activity Log"
          description="View recent test results and execution history"
          color="zinc"
        />
      </div>

      {/* Running tests */}
      {running.length > 0 && (
        <div className="mb-8">
          <h2 className="text-lg font-bold text-zinc-900 mb-3">
            Currently Running
          </h2>
          <div className="space-y-2">
            {running.map((exec) => (
              <Link
                key={exec.id}
                href={`/dashboard/tests/${exec.id}/results`}
                className="flex items-center gap-3 p-4 border border-blue-100 bg-blue-50/30 rounded-xl hover:bg-blue-50 transition-colors"
              >
                <Loader2
                  size={18}
                  className="text-blue-500 animate-spin"
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-zinc-900 truncate">
                    {exec.test_name}
                  </p>
                  <p className="text-xs text-zinc-500">
                    {exec.progress}% complete
                  </p>
                </div>
                <ArrowRight
                  size={16}
                  className="text-zinc-400"
                />
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Recent executions */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-bold text-zinc-900">
            Recent Runs
          </h2>
          {executions.length > 5 && (
            <Link
              href="/dashboard/tests"
              className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
            >
              View all →
            </Link>
          )}
        </div>
        {recent.length === 0 ? (
          <div className="text-center py-12 text-zinc-400 border border-dashed border-zinc-200 rounded-xl">
            <p className="text-sm">No test runs yet.</p>
            <p className="text-xs mt-1 text-zinc-300">
              Record or define a test to get started.
            </p>
          </div>
        ) : (
          <div className="border border-zinc-200 rounded-xl bg-white divide-y divide-zinc-100">
            {recent.map((exec) => (
              <Link
                key={exec.id}
                href={`/dashboard/tests/${exec.id}/results`}
                className="flex items-center gap-3 px-5 py-3.5 hover:bg-zinc-50/60 transition-colors"
              >
                {exec.status === "completed" ? (
                  <CheckCircle2
                    size={16}
                    className="text-emerald-500"
                  />
                ) : exec.status === "failed" ? (
                  <XCircle
                    size={16}
                    className="text-red-500"
                  />
                ) : exec.status === "running" ? (
                  <Loader2
                    size={16}
                    className="text-blue-500 animate-spin"
                  />
                ) : (
                  <Clock
                    size={16}
                    className="text-zinc-400"
                  />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-zinc-900 truncate">
                    {exec.test_name}
                  </p>
                </div>
                <span className="text-xs text-zinc-400">
                  {new Date(
                    exec.created_at
                  ).toLocaleDateString()}
                </span>
                <ArrowRight
                  size={14}
                  className="text-zinc-300"
                />
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ---- Sub-components ---- */

function StatCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-3 p-4 border border-zinc-200 rounded-xl bg-white">
      {icon}
      <div>
        <p className="text-2xl font-bold text-zinc-900">{value}</p>
        <p className="text-xs text-zinc-500">{label}</p>
      </div>
    </div>
  );
}

function QuickAction({
  href,
  title,
  description,
  color,
}: {
  href: string;
  title: string;
  description: string;
  color: string;
}) {
  const bgColor =
    color === "indigo"
      ? "bg-gradient-to-br from-indigo-500 to-violet-600 text-white"
      : "bg-white border border-zinc-200 text-zinc-900";
  const descColor =
    color === "indigo" ? "text-indigo-100" : "text-zinc-500";

  return (
    <Link
      href={href}
      className={`block p-5 rounded-xl transition-transform hover:scale-[1.02] ${bgColor}`}
    >
      <p className="font-semibold text-sm">{title}</p>
      <p className={`text-xs mt-1 ${descColor}`}>{description}</p>
    </Link>
  );
}
