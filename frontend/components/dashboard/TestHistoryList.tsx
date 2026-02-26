"use client";

import Link from "next/link";
import type { TestExecution } from "@/lib/types";
import {
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  ExternalLink,
  FileText,
  Eye,
  Trash2,
} from "lucide-react";

interface TestHistoryListProps {
  executions: TestExecution[];
  loading: boolean;
  onDelete?: (executionId: string) => void;
}

export default function TestHistoryList({
  executions,
  loading,
  onDelete,
}: TestHistoryListProps) {
  function timeAgo(iso: string) {
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
  }

  function statusIcon(status: TestExecution["status"]) {
    switch (status) {
      case "completed":
        return <CheckCircle2 size={18} className="text-emerald-500" />;
      case "failed":
        return <XCircle size={18} className="text-red-500" />;
      case "running":
        return <Loader2 size={18} className="text-blue-500 animate-spin" />;
      default:
        return <Clock size={18} className="text-gray-400" />;
    }
  }

  function passBadge(execution: TestExecution) {
    const scheduledBadge = execution.is_scheduled ? (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-violet-50 text-violet-700 mr-1.5">
        Scheduled
      </span>
    ) : null;
    if (execution.status === "running") {
      return (
        <>
          {scheduledBadge}
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700">
            running…
          </span>
        </>
      );
    }
    if (execution.status === "pending") {
      return (
        <>
          {scheduledBadge}
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500">
            pending
          </span>
        </>
      );
    }
    if (execution.status === "failed" && execution.error_message) {
      return (
        <>
          {scheduledBadge}
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-700">
            error
          </span>
        </>
      );
    }
    return (
      <>
        {scheduledBadge}
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700">
          completed
        </span>
      </>
    );
  }

  function formatRuntime(sec: number | null) {
    if (sec == null) return "—";
    return sec < 60 ? `${sec.toFixed(1)}s` : `${(sec / 60).toFixed(1)}m`;
  }

  function shortenUrl(url: string) {
    try {
      const u = new URL(url);
      const path =
        u.pathname.length > 15 ? u.pathname.slice(0, 15) + "…" : u.pathname;
      return u.hostname.replace("www.", "") + path;
    } catch {
      return url.slice(0, 30);
    }
  }

  if (loading) {
    return (
      <div className="animate-pulse space-y-3 mt-8">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-14 bg-gray-100 rounded-lg" />
        ))}
      </div>
    );
  }

  if (executions.length === 0) {
    return (
      <div className="mt-10">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Test History</h2>
        <p className="text-gray-400 text-sm">No test runs yet.</p>
      </div>
    );
  }

  return (
    <div className="mt-10">
      <h2 className="text-xl font-bold text-gray-900 mb-4">Test History</h2>

      <div className="border border-gray-200 rounded-xl bg-white divide-y divide-gray-100">
        {executions.map((exec) => (
          <div
            key={exec.id}
            className="flex items-center gap-4 px-5 py-3.5 hover:bg-gray-50/60 transition-colors group"
          >
            {/* Status icon */}
            {statusIcon(exec.status)}

            {/* Name / description */}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-gray-900 truncate">
                {exec.test_name}
              </p>
              <p className="text-xs text-gray-500 truncate mt-0.5">
                {exec.description}
              </p>
            </div>

            {/* Badge */}
            {passBadge(exec)}

            {/* Runtime */}
            <span className="text-xs text-gray-500 font-mono whitespace-nowrap w-14 text-right">
              {formatRuntime(exec.total_runtime_sec)}
            </span>

            {/* URL */}
            <a
              href={exec.url}
              target="_blank"
              rel="noopener noreferrer"
              className="hidden md:flex items-center gap-1 text-xs text-gray-500 hover:text-indigo-600 transition-colors whitespace-nowrap"
            >
              <ExternalLink size={12} />
              {shortenUrl(exec.url)}
            </a>

            {/* Time ago */}
            <span className="text-xs text-gray-400 whitespace-nowrap hidden sm:block">
              <Clock size={12} className="inline mr-1" />
              {timeAgo(exec.created_at)}
            </span>

            {/* Actions */}
            <div className="flex items-center gap-2">
              {exec.status === "completed" && (
                <Link
                  href={`/dashboard/tests/${exec.id}/results`}
                  className="flex items-center gap-1 text-xs text-gray-500 hover:text-indigo-600 transition-colors whitespace-nowrap"
                >
                  <FileText size={13} />
                  View Logs
                </Link>
              )}
              {exec.status === "running" && (
                <Link
                  href={`/dashboard/tests/${exec.id}/results`}
                  className="flex items-center gap-1 text-xs text-blue-500 hover:text-blue-700 transition-colors whitespace-nowrap"
                >
                  <Eye size={13} />
                  Live View
                </Link>
              )}
              {onDelete && (
                <button
                  type="button"
                  onClick={() => onDelete(exec.id)}
                  className="flex items-center gap-1 text-xs text-gray-400 hover:text-red-600 transition-colors whitespace-nowrap p-1 rounded hover:bg-red-50"
                  aria-label="Delete test execution"
                >
                  <Trash2 size={13} />
                  Delete
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
