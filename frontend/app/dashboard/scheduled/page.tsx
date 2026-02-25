"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import Link from "next/link";
import { testsApi, schedulesApi, type ScheduleResponse } from "@/lib/api";
import type { Test } from "@/lib/types";
import { NewScheduleModal, type NewScheduleForm } from "@/components/dashboard/NewScheduleModal";
import { Button } from "@/components/ui/button";
import { Calendar, RefreshCw, Pencil, ChevronLeft, ChevronRight, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";

function mapScheduleToItem(s: ScheduleResponse): ScheduledItem {
  return {
    id: String(s.id),
    testId: s.test_id,
    testName: s.test_name,
    scheduleType: s.schedule_type,
    runOnDays: s.run_on_days ?? [],
    runOnDate: s.run_on_date ?? "",
    runAt: s.run_at ?? "09:00",
    startsOn: "",
    repeatEvery: s.repeat_every ?? 0,
    repeatUnit: s.repeat_unit ?? "minutes",
    name: s.name ?? "",
    lastRun: s.last_run_at ?? null,
  };
}

type ViewMode = "today" | "week" | "list";

export interface ScheduledItem {
  id: string;
  testId: string;
  testName: string;
  testDescription?: string;
  scheduleType: "weekly" | "once" | "daily" | "custom";
  runOnDays: number[];
  runOnDate: string;
  runAt: string;
  startsOn: string;
  repeatEvery: number;
  repeatUnit: string;
  name: string;
  lastRun: string | null;
}

function getNextRunDate(item: ScheduledItem): Date | null {
  const [h, m] = item.runAt.split(":").map(Number);
  const now = new Date();
  if (item.scheduleType === "once") {
    if (!item.runOnDate) return null;
    const d = new Date(item.runOnDate + "T" + item.runAt);
    return d.getTime() >= now.getTime() ? d : null;
  }
  if (item.scheduleType === "daily") {
    const d = new Date(now);
    d.setHours(h, m, 0, 0);
    if (d.getTime() <= now.getTime()) d.setDate(d.getDate() + 1);
    return d;
  }
  if (item.scheduleType === "weekly" && item.runOnDays.length > 0) {
    const today = now.getDay();
    for (let i = 0; i <= 7; i++) {
      const day = (today + i) % 7;
      if (!item.runOnDays.includes(day)) continue;
      const d = new Date(now);
      d.setDate(d.getDate() + (i === 0 ? (now.getHours() * 60 + now.getMinutes() < h * 60 + m ? 0 : 7) : i));
      d.setHours(h, m, 0, 0);
      return d;
    }
  }
  return null;
}

function formatScheduleLabel(item: ScheduledItem): string {
  const d = item.runOnDate ? new Date(item.runOnDate) : null;
  const time = item.runAt ? (() => {
    const [h, m] = item.runAt.split(":").map(Number);
    const period = h >= 12 ? "PM" : "AM";
    const hour = h % 12 || 12;
    return `${hour}:${String(m).padStart(2, "0")} ${period}`;
  })() : "9:00 AM";
  if (item.scheduleType === "once" && d) {
    return `Once on ${d.toLocaleDateString("en-US", { month: "numeric", day: "numeric", year: "numeric" })} at ${time}`;
  }
  if (item.scheduleType === "daily") return `Daily at ${time}`;
  if (item.scheduleType === "weekly") return `Weekly at ${time}`;
  if (item.scheduleType === "custom") return `Every ${item.repeatEvery} ${item.repeatUnit}`;
  return "Once";
}

export default function DashboardScheduledPage() {
  const { toast } = useToast();
  const [tests, setTests] = useState<Test[]>([]);
  const [schedules, setSchedules] = useState<ScheduledItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<ViewMode>("list");
  const [modalOpen, setModalOpen] = useState(false);
  const [weekOffset, setWeekOffset] = useState(0);

  const fetchSchedules = useCallback(async () => {
    try {
      const data = await schedulesApi.list();
      setSchedules((Array.isArray(data) ? data : []).map(mapScheduleToItem));
    } catch {
      setSchedules([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    testsApi.list().then((data) => setTests(Array.isArray(data) ? data : [])).catch(() => setTests([]));
  }, []);

  useEffect(() => {
    fetchSchedules();
  }, [fetchSchedules]);

  const handleCreateSchedule = async (form: NewScheduleForm) => {
    try {
      await schedulesApi.create({
        test_id: form.testId,
        schedule_type: form.scheduleType,
        run_on_days: form.runOnDays.length ? form.runOnDays : undefined,
        run_on_date: form.runOnDate || undefined,
        run_at: form.runAt || "09:00",
        starts_on: form.startsOn || undefined,
        repeat_every: form.repeatEvery,
        repeat_unit: form.repeatUnit,
        name: form.name || undefined,
      });
      toast({ title: "Schedule created", description: "The test will run at the scheduled time." });
      await fetchSchedules();
    } catch (e) {
      toast({
        title: "Failed to create schedule",
        description: e instanceof Error ? e.message : "Unknown error",
        variant: "destructive",
      });
      throw e;
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await schedulesApi.delete(id);
      setSchedules((prev) => prev.filter((s) => s.id !== id));
      toast({ title: "Schedule deleted" });
    } catch (e) {
      toast({
        title: "Failed to delete schedule",
        description: e instanceof Error ? e.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  const today = useMemo(() => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  }, []);

  const weekStart = useMemo(() => {
    const d = new Date(today);
    d.setDate(d.getDate() - d.getDay() + weekOffset * 7);
    d.setHours(0, 0, 0, 0);
    return d;
  }, [today, weekOffset]);

  const weekDays = useMemo(() => {
    return Array.from({ length: 7 }, (_, i) => {
      const d = new Date(weekStart);
      d.setDate(d.getDate() + i);
      return d;
    });
  }, [weekStart]);

  const schedulesForDay = (date: Date) => {
    const dayStart = new Date(date);
    dayStart.setHours(0, 0, 0, 0);
    const dayEnd = new Date(date);
    dayEnd.setHours(23, 59, 59, 999);
    return schedules.filter((s) => {
      const next = getNextRunDate(s);
      if (!next) return false;
      return next.getTime() >= dayStart.getTime() && next.getTime() <= dayEnd.getTime();
    });
  };

  const todaySchedules = schedulesForDay(today);
  const isToday = (d: Date) => d.toDateString() === today.toDateString();

  return (
    <div className="max-w-6xl">
      {/* Project row (optional - match screenshots) */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">
            testt
          </h1>
          <a
            href="https://www.google.com/travel/flights"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-gray-500 hover:text-gray-700 inline-flex items-center gap-1 mt-0.5"
          >
            https://www.google.com/travel/flights
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="border-gray-300 text-gray-700">
            <Pencil className="h-4 w-4 mr-1.5" />
            Project settings
          </Button>
          <Link href="/dashboard/tests">
            <Button variant="outline" size="sm" className="border-gray-300 text-gray-700">
              <ChevronLeft className="h-4 w-4 mr-1.5" />
              All projects
            </Button>
          </Link>
        </div>
      </div>

      {/* Tests | Scheduled tabs */}
      <div className="flex gap-1 border-b border-gray-200 mb-6">
        <Link
          href="/dashboard/tests"
          className="px-4 py-2 text-sm font-medium border-b-2 border-transparent text-gray-500 hover:text-gray-700"
        >
          Tests
        </Link>
        <span className="px-4 py-2 text-sm font-medium border-b-2 border-gray-900 text-gray-900">
          Scheduled
        </span>
      </div>

      {/* Section title + controls */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Scheduled Tests</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            {view === "today"
              ? new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" })
              : "All Scheduled Tests"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            onClick={() => setModalOpen(true)}
            className="bg-gray-900 text-white hover:bg-gray-800"
          >
            <Calendar className="h-4 w-4 mr-2" />
            Schedule Test
          </Button>
          <button
            type="button"
            onClick={() => { setLoading(true); fetchSchedules(); }}
            className="p-2 rounded-md border border-gray-200 bg-white text-gray-600 hover:bg-gray-50"
            aria-label="Refresh"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          <div className="flex rounded-md border border-gray-200 bg-white p-0.5 ml-2">
            {(["today", "week", "list"] as const).map((v) => (
              <button
                key={v}
                type="button"
                onClick={() => setView(v)}
                className={cn(
                  "rounded px-3 py-1.5 text-sm font-medium capitalize transition-colors",
                  view === v ? "bg-gray-900 text-white" : "text-gray-600 hover:bg-gray-100"
                )}
              >
                {v}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Today view */}
      {view === "today" && (
        <div className="rounded-lg border border-gray-200 bg-white min-h-[320px] flex items-center justify-center">
          {todaySchedules.length === 0 ? (
            <p className="text-gray-500 text-sm">No tests scheduled for today.</p>
          ) : (
            <ul className="w-full p-4 space-y-3">
              {todaySchedules.map((s) => (
                <li
                  key={s.id}
                  className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4"
                >
                  <div>
                    <p className="font-medium text-gray-900">{s.name || s.testName}</p>
                    <p className="text-sm text-gray-500">
                      {(() => {
                        const [h, m] = s.runAt.split(":").map(Number);
                        const period = h >= 12 ? "PM" : "AM";
                        const hour = h % 12 || 12;
                        return `${hour}:${String(m).padStart(2, "0")} ${period} - ${s.scheduleType === "once" ? "Once" : s.scheduleType}`;
                      })()}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDelete(s.id)}
                    className="p-2 text-gray-400 hover:bg-red-50 hover:text-red-600 rounded"
                    aria-label="Delete"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Week view */}
      {view === "week" && (
        <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
          <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setWeekOffset((o) => o - 1)}
                className="p-2 rounded border border-gray-200 hover:bg-gray-50 text-gray-600"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={() => setWeekOffset((o) => o + 1)}
                className="p-2 rounded border border-gray-200 hover:bg-gray-50 text-gray-600"
                aria-label="Next week"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
            <span className="text-sm font-medium text-gray-700">
              Week of {weekStart.toLocaleDateString("en-US", { month: "2-digit", day: "2-digit", year: "2-digit" })}
            </span>
          </div>
          <div className="grid grid-cols-7 divide-x divide-gray-100 min-h-[320px]">
            {weekDays.map((d) => {
              const daySchedules = schedulesForDay(d);
              return (
                <div key={d.toISOString()} className={cn("flex flex-col bg-gray-50/50", isToday(d) && "bg-white")}>
                  <div className="px-2 py-2 text-center text-sm font-medium text-gray-700 border-b border-gray-100">
                    {d.toLocaleDateString("en-US", { weekday: "short" })} {d.getMonth() + 1}/{d.getDate()}
                  </div>
                  <div className="flex-1 p-2 space-y-2 overflow-y-auto">
                    {daySchedules.length === 0 ? (
                      <p className="text-xs text-gray-400 text-center py-4">No tests</p>
                    ) : (
                      daySchedules.map((s) => (
                        <div
                          key={s.id}
                          className="rounded border border-gray-200 bg-white p-2 group"
                        >
                          <p className="text-sm font-medium text-gray-900 truncate">{s.name || s.testName}</p>
                          <p className="text-xs text-gray-500">
                            {(() => {
                              const [h, m] = s.runAt.split(":").map(Number);
                              const period = h >= 12 ? "PM" : "AM";
                              const hour = h % 12 || 12;
                              return `${hour}:${String(m).padStart(2, "0")} ${period} - Once`;
                            })()}
                          </p>
                          <button
                            type="button"
                            onClick={() => handleDelete(s.id)}
                            className="mt-1 p-1 text-gray-400 hover:text-red-600 opacity-0 group-hover:opacity-100"
                          >
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* List view */}
      {view === "list" && (
        <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-gray-500 font-medium">
                <th className="py-3 pl-4">Name</th>
                <th className="py-3">Type</th>
                <th className="py-3">Schedule</th>
                <th className="py-3">Last Run</th>
                <th className="py-3 pr-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-gray-500">
                    Loading…
                  </td>
                </tr>
              ) : schedules.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-gray-500">
                    No scheduled tests. Click &quot;Schedule Test&quot; to add one.
                  </td>
                </tr>
              ) : (
                schedules.map((s) => (
                  <tr key={s.id} className="border-b border-gray-50 hover:bg-gray-50/80">
                    <td className="py-3 pl-4">
                      <p className="font-medium text-gray-900">{s.name || s.testName}</p>
                      <p className="text-xs text-gray-500">Test: {s.testName}</p>
                    </td>
                    <td className="py-3">
                      <span className="inline-flex rounded bg-green-600 text-white text-xs font-medium px-2 py-0.5">
                        Test
                      </span>
                    </td>
                    <td className="py-3 text-gray-700">{formatScheduleLabel(s)}</td>
                    <td className="py-3 text-gray-500">{s.lastRun ?? "Never"}</td>
                    <td className="py-3 pr-4 text-right">
                      <button
                        type="button"
                        onClick={() => handleDelete(s.id)}
                        className="p-2 text-gray-400 hover:bg-red-50 hover:text-red-600 rounded"
                        aria-label="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      <NewScheduleModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onCreate={handleCreateSchedule}
        tests={tests}
      />
    </div>
  );
}
