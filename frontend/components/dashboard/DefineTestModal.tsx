"use client";

import { useState } from "react";
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
import { Loader2 } from "lucide-react";
import type { Test } from "@/lib/types";

interface DefineTestModalProps {
  open: boolean;
  onClose: () => void;
  onCreate: (data: Omit<Test, "id" | "created_at" | "updated_at">) => Promise<void>;
}

export default function DefineTestModal({ open, onClose, onCreate }: DefineTestModalProps) {
  const [testName, setTestName] = useState("");
  const [url, setUrl] = useState("");
  const [description, setDescription] = useState("");
  const [stepsText, setStepsText] = useState("");
  const [expectedBehavior, setExpectedBehavior] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setTestName("");
    setUrl("");
    setDescription("");
    setStepsText("");
    setExpectedBehavior("");
    setError(null);
  }

  async function handleCreate() {
    setError(null);
    if (!testName.trim()) return setError("Test name is required.");
    if (!url.trim()) return setError("URL is required.");
    const lines = stepsText.split("\n").map((l) => l.trim()).filter(Boolean);
    if (lines.length === 0) return setError("At least one step is required.");

    const steps = lines.map((instruction) => ({ kind: "act" as const, instruction }));

    setSaving(true);
    try {
      await onCreate({
        test_name: testName.trim(),
        url: url.trim(),
        steps,
        description: description.trim(),
        expected_behavior: expectedBehavior.trim(),
      });
      reset();
      onClose();
    } catch (err) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) { reset(); onClose(); }
      }}
    >
      <DialogContent className="max-w-lg bg-white border-gray-200 shadow-xl [&>button]:top-4 [&>button]:right-4">
        <DialogHeader>
          <DialogTitle>Define New Test</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="grid gap-2">
            <label className="text-sm font-medium text-gray-700">Test name</label>
            <Input
              value={testName}
              onChange={(e) => setTestName(e.target.value)}
              placeholder="e.g. Login flow"
              className="border-gray-300"
            />
          </div>

          <div className="grid gap-2">
            <label className="text-sm font-medium text-gray-700">URL</label>
            <Input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://..."
              className="border-gray-300"
            />
          </div>

          <div className="grid gap-2">
            <label className="text-sm font-medium text-gray-700">
              Description{" "}
              <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <Input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. Verifies the login flow works end-to-end"
              className="border-gray-300"
            />
          </div>

          <div className="grid gap-2">
            <label className="text-sm font-medium text-gray-700">
              Steps{" "}
              <span className="text-gray-400 font-normal">(one per line, plain English)</span>
            </label>
            <Textarea
              value={stepsText}
              onChange={(e) => setStepsText(e.target.value)}
              placeholder={"Click the login button\nType 'user@example.com' in the email field\nClick submit"}
              rows={6}
              className="border-gray-300 font-mono text-sm"
            />
          </div>

          <div className="grid gap-2">
            <label className="text-sm font-medium text-gray-700">
              Expected behavior{" "}
              <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <Textarea
              value={expectedBehavior}
              onChange={(e) => setExpectedBehavior(e.target.value)}
              placeholder="e.g. User should be redirected to the dashboard after login"
              rows={2}
              className="border-gray-300"
            />
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => { reset(); onClose(); }} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleCreate} disabled={saving}>
            {saving ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Saving…
              </>
            ) : (
              "Create test"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}