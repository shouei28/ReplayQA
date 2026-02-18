"use client";

import { useState } from "react";
import type { Test } from "@/lib/types";
import {
  Play,
  Settings2,
  Copy,
  Trash2,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

interface TestListProps {
  tests: Test[];
  loading: boolean;
  onRun: (test: Test) => void;
  onDelete: (test: Test) => void;
  onRunSelected: (ids: string[]) => void;
}

const PAGE_SIZE = 10;

export default function TestList({
  tests,
  loading,
  onRun,
  onDelete,
  onRunSelected,
}: TestListProps) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [page, setPage] = useState(1);

  const totalPages = Math.max(1, Math.ceil(tests.length / PAGE_SIZE));
  const paginated = tests.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const allSelected = paginated.length > 0 && paginated.every((t) => selectedIds.has(t.id));

  function toggleAll() {
    if (allSelected) {
      const next = new Set(selectedIds);
      paginated.forEach((t) => next.delete(t.id));
      setSelectedIds(next);
    } else {
      const next = new Set(selectedIds);
      paginated.forEach((t) => next.add(t.id));
      setSelectedIds(next);
    }
  }

  function toggleOne(id: string) {
    const next = new Set(selectedIds);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelectedIds(next);
  }

  function formatDate(iso: string) {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "numeric",
      day: "numeric",
      year: "numeric",
    });
  }

  function shortenUrl(url: string) {
    try {
      const u = new URL(url);
      const path = u.pathname.length > 12 ? u.pathname.slice(0, 12) + "…" : u.pathname;
      return u.hostname.replace("www.", "") + path;
    } catch {
      return url.slice(0, 30);
    }
  }

  if (loading) {
    return (
      <div className="animate-pulse space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-16 bg-gray-100 rounded-lg" />
        ))}
      </div>
    );
  }

  return (
    <div>
      {/* Header controls */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h2 className="text-xl font-bold text-gray-900">Your Tests</h2>
          <button
            onClick={toggleAll}
            className="px-3 py-1 text-xs font-medium border border-gray-300 rounded-md bg-white hover:bg-gray-50 transition-colors"
          >
            {allSelected ? "Deselect All" : "Select All"}
          </button>
          {selectedIds.size > 0 && (
            <button
              onClick={() => onRunSelected(Array.from(selectedIds))}
              className="px-3 py-1 text-xs font-medium bg-gray-900 text-white rounded-md hover:bg-gray-800 transition-colors"
            >
              Run Selected Tests
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button className="px-4 py-2 text-sm font-medium border border-gray-300 rounded-lg bg-white hover:bg-gray-50 transition-colors">
            Record New Test
          </button>
          <button className="px-4 py-2 text-sm font-medium border border-gray-300 rounded-lg bg-white hover:bg-gray-50 transition-colors">
            Define New Test
          </button>
        </div>
      </div>

      {/* Test rows */}
      {tests.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <p className="text-lg">No saved tests yet</p>
          <p className="text-sm mt-1">Record or define a test to get started.</p>
        </div>
      ) : (
        <div className="border border-gray-200 rounded-xl bg-white divide-y divide-gray-100">
          {paginated.map((test) => (
            <div
              key={test.id}
              className="flex items-center gap-4 px-5 py-3.5 hover:bg-gray-50/60 transition-colors group"
            >
              {/* Checkbox */}
              <input
                type="checkbox"
                checked={selectedIds.has(test.id)}
                onChange={() => toggleOne(test.id)}
                className="w-4 h-4 rounded border-gray-300 accent-indigo-600 cursor-pointer"
              />

              {/* Info */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-gray-900 truncate">
                  {test.test_name}
                </p>
                <p className="text-xs text-gray-500 truncate mt-0.5">
                  {test.description}
                </p>
              </div>

              {/* Meta */}
              <span className="text-xs text-gray-400 whitespace-nowrap hidden sm:block">
                created {formatDate(test.created_at)}
              </span>

              {/* URL */}
              <a
                href={test.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-xs text-gray-500 hover:text-indigo-600 transition-colors whitespace-nowrap"
              >
                <ExternalLink size={12} />
                {shortenUrl(test.url)}
              </a>

              {/* Actions */}
              <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={() => onRun(test)}
                  className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-gray-700 hover:text-indigo-600 hover:bg-indigo-50 rounded-md transition-colors"
                  title="Run test"
                >
                  <Play size={13} fill="currentColor" />
                  Run
                </button>
                <button
                  className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
                  title="Settings"
                >
                  <Settings2 size={14} />
                </button>
                <button
                  className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
                  title="Duplicate"
                >
                  <Copy size={14} />
                </button>
                <button
                  onClick={() => onDelete(test)}
                  className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-md transition-colors"
                  title="Delete"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4 text-sm text-gray-500">
          <span>
            Showing {(page - 1) * PAGE_SIZE + 1}–
            {Math.min(page * PAGE_SIZE, tests.length)} of {tests.length}
          </span>
          <div className="flex items-center gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
              className="px-2 py-1 border rounded-md disabled:opacity-30 hover:bg-gray-50 transition-colors"
            >
              <ChevronLeft size={16} />
            </button>
            <span className="text-xs">
              Page {page} of {totalPages}
            </span>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage(page + 1)}
              className="px-2 py-1 border rounded-md disabled:opacity-30 hover:bg-gray-50 transition-colors"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
