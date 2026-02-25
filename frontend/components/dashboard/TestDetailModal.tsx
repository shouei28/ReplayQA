"use client";

import { useState, useEffect } from "react";
import type { Test, StepDefinition } from "@/lib/types";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, Plus, Trash2 } from "lucide-react";

interface TestDetailModalProps {
  test: Test | null;
  open: boolean;
  onClose: () => void;
  onSave: (testId: string, updates: Partial<Test>) => Promise<void>;
}

export default function TestDetailModal({
  test,
  open,
  onClose,
  onSave,
}: TestDetailModalProps) {
  const [testName, setTestName] = useState("");
  const [description, setDescription] = useState("");
  const [url, setUrl] = useState("");
  const [expectedBehavior, setExpectedBehavior] = useState("");
  const [steps, setSteps] = useState<StepDefinition[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (test) {
      setTestName(test.test_name);
      setDescription(test.description ?? "");
      setUrl(test.url ?? "");
      setExpectedBehavior(test.expected_behavior ?? "");
      setSteps(Array.isArray(test.steps) ? [...test.steps] : []);
    }
  }, [test]);

  const stepKind = (s: StepDefinition) => s.kind ?? s.type ?? "act";

  function addStep(kind: "goto" | "act" = "act") {
    if (kind === "goto") {
      setSteps((prev) => [{ kind: "goto", url: "" }, ...prev]);
    } else {
      setSteps((prev) => [...prev, { kind: "act", instruction: "" }]);
    }
  }

  function removeStep(index: number) {
    setSteps((prev) => prev.filter((_, i) => i !== index));
  }

  function updateStep(index: number, field: keyof StepDefinition, value: string) {
    setSteps((prev) => {
      const next = [...prev];
      const step = { ...next[index] };
      (step as Record<string, unknown>)[field] = value;
      if (!step.kind && !step.type) step.kind = "act";
      next[index] = step;
      return next;
    });
  }

  async function handleSave() {
    if (!test) return;
    setSaving(true);
    try {
      await onSave(test.id, {
        test_name: testName,
        description,
        url,
        expected_behavior: expectedBehavior,
        steps,
      });
      onClose();
    } finally {
      setSaving(false);
    }
  }

  if (!test) return null;

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh] p-0 gap-0 bg-white border-gray-200 shadow-xl overflow-hidden [&>button]:top-4 [&>button]:right-4">
        <div className="flex flex-col h-[85vh] max-h-[85vh] min-h-0">
          <DialogHeader className="shrink-0 px-6 pt-6 pb-4">
            <DialogTitle>Edit Test: {test.test_name}</DialogTitle>
          </DialogHeader>

          <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden px-6 space-y-4 py-2">
          {/* Basic info */}
          <div className="grid gap-4">
            <div className="grid gap-2">
              <label className="text-sm font-medium text-gray-700">Test name</label>
              <Input
                value={testName}
                onChange={(e) => setTestName(e.target.value)}
                className="border-gray-300"
              />
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium text-gray-700">Description</label>
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                className="border-gray-300"
              />
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium text-gray-700">URL</label>
              <Input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                className="border-gray-300"
              />
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium text-gray-700">Expected behavior</label>
              <Textarea
                value={expectedBehavior}
                onChange={(e) => setExpectedBehavior(e.target.value)}
                rows={2}
                className="border-gray-300"
              />
            </div>
          </div>

          {/* Steps */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-gray-700">Steps</label>
              <div className="flex gap-1">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => addStep("goto")}
                  className="h-8 text-xs"
                >
                  <Plus size={12} className="mr-1" />
                  Goto
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => addStep("act")}
                  className="h-8 text-xs"
                >
                  <Plus size={12} className="mr-1" />
                  Act
                </Button>
              </div>
            </div>
            <div className="space-y-2 max-h-64 overflow-y-auto border border-gray-200 rounded-lg p-3 bg-gray-50/50">
              {steps.length === 0 ? (
                <p className="text-sm text-gray-500 py-4 text-center">No steps yet</p>
              ) : (
                steps.map((step, i) => (
                  <div
                    key={i}
                    className="flex gap-2 items-start p-2 bg-white rounded border border-gray-200"
                  >
                    <span className="text-xs text-gray-400 mt-2.5 shrink-0">
                      {i + 1}
                    </span>
                    <div className="flex-1 min-w-0 space-y-2">
                      {stepKind(step) === "goto" ? (
                        <div className="grid gap-1">
                          <span className="text-xs font-medium text-indigo-600">Goto</span>
                          <Input
                            value={step.url ?? ""}
                            onChange={(e) => updateStep(i, "url", e.target.value)}
                            placeholder="https://..."
                            className="h-8 text-sm border-gray-300"
                          />
                        </div>
                      ) : (
                        <>
                          <div className="grid gap-1">
                            <span className="text-xs font-medium text-indigo-600">Act</span>
                            <Input
                              value={step.instruction ?? ""}
                              onChange={(e) => updateStep(i, "instruction", e.target.value)}
                              placeholder="Instruction (e.g. Click the button)"
                              className="h-8 text-sm border-gray-300"
                            />
                          </div>
                          <div className="flex gap-2 flex-wrap">
                            <Input
                              value={step.selector ?? ""}
                              onChange={(e) => updateStep(i, "selector", e.target.value)}
                              placeholder="Selector (optional)"
                              className="h-7 text-xs flex-1 min-w-[120px] border-gray-300"
                            />
                            <Input
                              value={step.method ?? ""}
                              onChange={(e) => updateStep(i, "method", e.target.value)}
                              placeholder="Method (click, fill, etc.)"
                              className="h-7 text-xs w-24 border-gray-300"
                            />
                          </div>
                        </>
                      )}
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 shrink-0 text-gray-400 hover:text-red-600"
                      onClick={() => removeStep(i)}
                      aria-label="Remove step"
                    >
                      <Trash2 size={14} />
                    </Button>
                  </div>
                ))
              )}
            </div>
          </div>
          </div>

          <DialogFooter className="shrink-0 border-t border-gray-200 px-6 py-4 bg-white">
          <Button variant="outline" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Saving…
              </>
            ) : (
              "Save changes"
            )}
          </Button>
          </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  );
}
