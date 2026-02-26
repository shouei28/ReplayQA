"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Test } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Calendar, Clock } from "lucide-react";

export type ScheduleType = "weekly" | "once" | "daily" | "custom";

export interface NewScheduleForm {
  testId: string;
  testName: string;
  scheduleType: ScheduleType;
  runOnDays: number[]; // 0 = Sun, 6 = Sat
  runOnDate: string; // YYYY-MM-DD
  runAt: string; // HH:mm
  startsOn: string; // YYYY-MM-DD or ""
  repeatEvery: number;
  repeatUnit: "minutes" | "hours" | "days";
  name: string;
}

const DAYS = [
  { label: "Sun", value: 0 },
  { label: "Mon", value: 1 },
  { label: "Tue", value: 2 },
  { label: "Wed", value: 3 },
  { label: "Thu", value: 4 },
  { label: "Fri", value: 5 },
  { label: "Sat", value: 6 },
];

const defaultForm: NewScheduleForm = {
  testId: "",
  testName: "",
  scheduleType: "weekly",
  runOnDays: [],
  runOnDate: "",
  runAt: "09:00",
  startsOn: "",
  repeatEvery: 30,
  repeatUnit: "minutes",
  name: "My scheduled test",
};

interface NewScheduleModalProps {
  open: boolean;
  onClose: () => void;
  onCreate: (form: NewScheduleForm) => void | Promise<void>;
  tests: Test[];
}

export function NewScheduleModal({
  open,
  onClose,
  onCreate,
  tests,
}: NewScheduleModalProps) {
  const [form, setForm] = useState<NewScheduleForm>(defaultForm);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const reset = () => {
    setForm(defaultForm);
    setError(null);
    setSubmitting(false);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleCreate = async () => {
    if (!form.testId) {
      setError("Please select a test.");
      return;
    }
    const runAtDate = new Date();
    const [h, m] = form.runAt.split(":").map(Number);
    runAtDate.setHours(h, m, 0, 0);
    if (form.scheduleType === "once" && form.runOnDate) {
      const d = new Date(form.runOnDate + "T" + form.runAt);
      if (d.getTime() < Date.now()) {
        setError("The selected date and time are in the past. Please choose a future time.");
        return;
      }
    }
    if (form.scheduleType === "daily" && runAtDate.getTime() < Date.now()) {
      setError("The selected date and time are in the past. Please choose a future time.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await onCreate(form);
      handleClose();
    } catch {
      setSubmitting(false);
    }
  };

  const toggleDay = (value: number) => {
    setForm((prev) => ({
      ...prev,
      runOnDays: prev.runOnDays.includes(value)
        ? prev.runOnDays.filter((d) => d !== value)
        : [...prev.runOnDays, value],
    }));
  };

  if (!open) return null;

  return (
    <Dialog open={open} onOpenChange={(o) => !o && handleClose()}>
      <DialogContent className="border-gray-200 bg-white sm:max-w-lg rounded-lg shadow-lg">
        <DialogHeader>
          <DialogTitle className="text-gray-900 font-semibold text-lg">
            New Schedule
          </DialogTitle>
        </DialogHeader>

        <div className="grid gap-5 py-2">
          {/* Test Suite */}
          <div className="grid gap-2">
            <label className="text-sm font-medium text-gray-700">Test Suite</label>
            <select
              value={form.testId}
              onChange={(e) => {
                const t = tests.find((x) => x.id === e.target.value);
                setForm((prev) => ({
                  ...prev,
                  testId: e.target.value,
                  testName: t?.test_name ?? "",
                }));
              }}
              className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-0"
            >
              <option value="">Select a test...</option>
              {tests.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.test_name}
                </option>
              ))}
            </select>
          </div>

          {/* Schedule type */}
          <div className="grid gap-2">
            <label className="text-sm font-medium text-gray-700">Schedule</label>
            <div className="flex rounded-md border border-gray-200 bg-white p-0.5">
              {(["weekly", "once", "daily", "custom"] as const).map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => setForm((prev) => ({ ...prev, scheduleType: type }))}
                  className={cn(
                    "flex-1 rounded px-3 py-2 text-sm font-medium capitalize transition-colors",
                    form.scheduleType === type
                      ? "bg-gray-900 text-white"
                      : "text-gray-600 hover:bg-gray-100"
                  )}
                >
                  {type}
                </button>
              ))}
            </div>
          </div>

          {/* Weekly: Run on */}
          {form.scheduleType === "weekly" && (
            <div className="grid gap-2">
              <label className="text-sm font-medium text-gray-700">Run on</label>
              <div className="flex flex-wrap gap-2">
                {DAYS.map(({ label, value }) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => toggleDay(value)}
                    className={cn(
                      "rounded-md border px-3 py-2 text-sm font-medium transition-colors",
                      form.runOnDays.includes(value)
                        ? "border-gray-900 bg-gray-900 text-white"
                        : "border-gray-200 bg-white text-gray-700 hover:bg-gray-50"
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Once: Run on date */}
          {form.scheduleType === "once" && (
            <div className="grid gap-2">
              <label className="text-sm font-medium text-gray-700">Run on date</label>
              <div className="flex gap-2 items-center">
                <span className="flex items-center rounded-md border border-gray-300 bg-white px-3 py-2 text-gray-500">
                  <Calendar className="h-4 w-4 mr-2" />
                  <input
                    type="date"
                    value={form.runOnDate}
                    onChange={(e) => setForm((prev) => ({ ...prev, runOnDate: e.target.value }))}
                    className="bg-transparent text-gray-900 text-sm focus:outline-none"
                  />
                </span>
                <span className="flex items-center rounded-md border border-gray-300 bg-white px-3 py-2 text-gray-500">
                  <Clock className="h-4 w-4 mr-2" />
                  <input
                    type="time"
                    value={form.runAt}
                    onChange={(e) => setForm((prev) => ({ ...prev, runAt: e.target.value }))}
                    className="bg-transparent text-gray-900 text-sm focus:outline-none w-24"
                  />
                </span>
              </div>
            </div>
          )}

          {/* Weekly / Daily: Time */}
          {(form.scheduleType === "weekly" || form.scheduleType === "daily") && (
            <div className="grid gap-2">
              <label className="text-sm font-medium text-gray-700">
                {form.scheduleType === "daily" ? "Run daily at" : "Time"}
              </label>
              <div className="flex items-center rounded-md border border-gray-300 bg-white px-3 py-2 text-gray-500 w-fit">
                <Clock className="h-4 w-4 mr-2" />
                <input
                  type="time"
                  value={form.runAt}
                  onChange={(e) => setForm((prev) => ({ ...prev, runAt: e.target.value }))}
                  className="bg-transparent text-gray-900 text-sm focus:outline-none"
                />
              </div>
            </div>
          )}

          {/* Weekly: Starts on (optional) */}
          {form.scheduleType === "weekly" && (
            <div className="grid gap-2">
              <label className="text-sm font-medium text-gray-700">
                Starts on (optional)
              </label>
              <p className="text-xs text-gray-500">
                Leave empty to start immediately. Or pick a date when this schedule should begin.
              </p>
              <div className="flex items-center rounded-md border border-gray-300 bg-white px-3 py-2 text-gray-500 w-fit">
                <Calendar className="h-4 w-4 mr-2" />
                <input
                  type="date"
                  value={form.startsOn}
                  onChange={(e) => setForm((prev) => ({ ...prev, startsOn: e.target.value }))}
                  placeholder="Pick start date"
                  className="bg-transparent text-gray-900 text-sm focus:outline-none min-w-[140px]"
                />
              </div>
            </div>
          )}

          {/* Custom: Repeat every */}
          {form.scheduleType === "custom" && (
            <div className="grid gap-2">
              <label className="text-sm font-medium text-gray-700">Repeat every</label>
              <div className="flex gap-2 items-center">
                <Input
                  type="number"
                  min={1}
                  value={form.repeatEvery}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, repeatEvery: Number(e.target.value) || 1 }))
                  }
                  className="w-20 border-gray-300"
                />
                <select
                  value={form.repeatUnit}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      repeatUnit: e.target.value as "minutes" | "hours" | "days",
                    }))
                  }
                  className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
                >
                  <option value="minutes">Minutes</option>
                  <option value="hours">Hours</option>
                  <option value="days">Days</option>
                </select>
              </div>
            </div>
          )}

          {/* Name (optional) */}
          <div className="grid gap-2">
            <label className="text-sm font-medium text-gray-700">Name (optional)</label>
            <Input
              value={form.name}
              onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
              placeholder="My scheduled test"
              className="border-gray-300 bg-white text-gray-900"
            />
          </div>

          {error && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-red-600">
              {error}
            </div>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={submitting}
            className="border-gray-300 text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </Button>
          <Button
            onClick={handleCreate}
            disabled={submitting}
            className="bg-gray-900 text-white hover:bg-gray-800"
          >
            {submitting ? "Creating…" : "Create Schedule"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
