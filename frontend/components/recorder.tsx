"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Loader2,
  Circle,
  CircleDot,
  Trash2,
  Monitor,
  Square,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

const getBaseUrl = () =>
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api").replace(
      /\/$/,
      ""
    )
    : "http://127.0.0.1:8000/api";

/** Build Authorization header from stored JWT token */
const authHeaders = (): Record<string, string> => {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
};

/** Single recorded step (from browser actions only). */
interface RecordedStep {
  id: string;
  instruction: string;
  selector?: string;
  method: string;
  args: unknown[];
  target_coordinate?: string;
}

export function Recorder() {
  const { toast } = useToast();
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [browserbaseSessionId, setBrowserbaseSessionId] = useState<string | null>(null);
  const [liveViewUrl, setLiveViewUrl] = useState<string | null>(null);
  const [steps, setSteps] = useState<RecordedStep[]>([]);
  const [device] = useState("desktop");
  const [browser] = useState("chrome");
  const [recording, setRecording] = useState(false);
  const recordingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const liveViewRetryRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const stepsListRef = useRef<HTMLDivElement>(null);
  const prevStepsLengthRef = useRef(0);
  const sessionCleanupRef = useRef<{
    sessionId: string | null;
    browserbaseSessionId: string | null;
    device: string;
    browser: string;
  }>({ sessionId: null, browserbaseSessionId: null, device: "desktop", browser: "chrome" });

  useEffect(() => {
    sessionCleanupRef.current = {
      sessionId,
      browserbaseSessionId,
      device,
      browser,
    };
  }, [sessionId, browserbaseSessionId, device, browser]);

  useEffect(() => {
    if (steps.length > prevStepsLengthRef.current) {
      prevStepsLengthRef.current = steps.length;
      stepsListRef.current?.scrollTo({
        top: stepsListRef.current.scrollHeight,
        behavior: "smooth",
      });
    } else {
      prevStepsLengthRef.current = steps.length;
    }
  }, [steps.length]);

  useEffect(() => {
    return () => {
      const { sessionId: sid, browserbaseSessionId: bb, device: d, browser: b } =
        sessionCleanupRef.current;
      if (!sid) return;
      if (recordingIntervalRef.current) {
        clearInterval(recordingIntervalRef.current);
        recordingIntervalRef.current = null;
      }
      if (liveViewRetryRef.current) {
        clearInterval(liveViewRetryRef.current);
        liveViewRetryRef.current = null;
      }
      fetch(`${getBaseUrl()}/recorder/${sid}/end`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ browserbase_session_id: bb, device: d, browser: b }),
      }).catch(() => { });
    };
  }, []);

  const [endModalOpen, setEndModalOpen] = useState(false);
  const [saveName, setSaveName] = useState("");
  const [saveExpectedBehavior, setSaveExpectedBehavior] = useState("");
  const [saving, setSaving] = useState(false);

  const startSession = async () => {
    if (!url.trim()) {
      toast({ title: "URL required", description: "Enter a URL to start recording", variant: "destructive" });
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${getBaseUrl()}/recorder/start`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ url: url.trim(), device, browser }),
      });
    
      if (!res.ok) {
        if (res.status === 429) {
          throw new Error("AI Quota Reached. Please try again later.");
        }
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || "Failed to start session");
      }
      
      const data = await res.json();
      setSessionId(data.session_id);
      setBrowserbaseSessionId(data.browserbase_session_id);
      setLiveViewUrl(data.live_view_url ?? null);

      await startRecording(
        data.session_id,
        data.browserbase_session_id,
        data.connect_url,
        data.device ?? "desktop",
        data.browser ?? "chrome",
        url.trim()
      );

      const sid = data.session_id;
      const bbSid = data.browserbase_session_id;
      let attempts = 0;
      const tryLiveView = async () => {
        attempts++;
        try {
          const r = await fetch(
            `${getBaseUrl()}/recorder/${sid}/live-view?browserbase_session_id=${encodeURIComponent(bbSid)}`,
            { method: "GET", credentials: "include", headers: { ...authHeaders() } }
          );
          if (r.ok) {
            const d = await r.json();
            if (d.live_view_url) {
              setLiveViewUrl(d.live_view_url);
              if (liveViewRetryRef.current) {
                clearInterval(liveViewRetryRef.current);
                liveViewRetryRef.current = null;
              }
            }
          }
        } catch {
          /* ignore */
        }
        if (attempts >= 8 && liveViewRetryRef.current) {
          clearInterval(liveViewRetryRef.current);
          liveViewRetryRef.current = null;
        }
      };
      liveViewRetryRef.current = setInterval(tryLiveView, 1500);
      tryLiveView();
      toast({ title: "Session started", description: "Recording is on. Interact in the browser to record steps." });
    } catch (e) {
      toast({
        title: "Failed to start",
        description: e instanceof Error ? e.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const startRecording = async (
    sid: string,
    browserbaseSid: string,
    connectUrl?: string,
    dev: string = "desktop",
    br: string = "chrome",
    initialUrl?: string
  ) => {
    if (!sid || !browserbaseSid) return;
    const res = await fetch(`${getBaseUrl()}/recorder/${sid}/start-recording`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({
        browserbase_session_id: browserbaseSid,
        connect_url: connectUrl,
        device: dev,
        browser: br,
        url: initialUrl,
      }),
    });
    if (!res.ok) throw new Error("Failed to start recording");
    setRecording(true);

    if (recordingIntervalRef.current) clearInterval(recordingIntervalRef.current);
    recordingIntervalRef.current = setInterval(async () => {
      try {
        const r = await fetch(`${getBaseUrl()}/recorder/${sid}/recorded-actions`, {
          method: "GET",
          credentials: "include",
          headers: { ...authHeaders() },
        });
        if (!r.ok) return;
        const data = await r.json();
        if (data.session_closed) {
          if (recordingIntervalRef.current) {
            clearInterval(recordingIntervalRef.current);
            recordingIntervalRef.current = null;
          }
          if (liveViewRetryRef.current) {
            clearInterval(liveViewRetryRef.current);
            liveViewRetryRef.current = null;
          }
          toast({
            title: "Session closed",
            description: "The recording session ended. Start a new one to continue.",
            variant: "destructive",
          });
          return;
        }
        if (data.recording !== undefined) setRecording(data.recording);
        const newActions = data.actions || [];
        if (newActions.length === 0) return;

        const newSteps: RecordedStep[] = newActions.map((a: Record<string, unknown>) => ({
          id: `step-${Date.now()}-${Math.random().toString(36).slice(2)}`,
          instruction: (a.description as string) ?? "",
          selector: a.selector as string | undefined,
          method: (a.method as string) ?? "click",
          args: (a.arguments as unknown[]) ?? [],
          target_coordinate: a.target_coordinate as string | undefined,
        }));

        setSteps((prev) => {
          let result = [...prev];
          for (const step of newSteps) {
            if (step.method !== "fill") {
              result.push(step);
              continue;
            }
            const last = result[result.length - 1];
            if (
              last?.method === "fill" &&
              last.selector === step.selector
            ) {
              const prevVal = (last.args[0] ?? "") as string;
              const newVal = (step.args[0] ?? "") as string;
              const merged = newVal.startsWith(prevVal) || prevVal.startsWith(newVal)
                ? (newVal.length >= prevVal.length ? newVal : prevVal)
                : prevVal + newVal;
              const part = last.instruction.split(" into the ").pop() || "field";
              result[result.length - 1] = {
                ...last,
                instruction: `Type "${merged}" into the ${part}`,
                args: [merged],
              };
            } else {
              result.push(step);
            }
          }
          return result;
        });
      } catch {
        /* ignore poll errors */
      }
    }, 1000);
  };

  const toggleRecording = async (sid: string, enabled: boolean) => {
    if (!sid) return;
    try {
      const res = await fetch(`${getBaseUrl()}/recorder/${sid}/toggle-recording`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ enabled }),
      });
      if (!res.ok) throw new Error("Failed to toggle");
      setRecording(enabled);
      toast({
        title: enabled ? "Recording on" : "Recording paused",
        description: enabled ? "Interactions will be recorded." : "Interactions are not recorded.",
      });
    } catch (e) {
      toast({
        title: "Toggle failed",
        description: e instanceof Error ? e.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  const removeStep = (id: string) => {
    setSteps((prev) => prev.filter((s) => s.id !== id));
  };

  /** Build payload for save-test: goto + act steps. */
  const buildStepsForSave = (): Array<{ kind: string; url?: string; instruction?: string; selector?: string; method?: string; target_coordinate?: string }> => {
    const out: Array<{ kind: string; url?: string; instruction?: string; selector?: string; method?: string; target_coordinate?: string }> = [];
    if (url.trim()) {
      out.push({ kind: "goto", url: url.trim() });
    }
    for (const step of steps) {
      if (step.method === "scrollto" && step.target_coordinate) {
        out.push({
          kind: "act",
          instruction: step.instruction,
          target_coordinate: step.target_coordinate,
        });
      } else {
        out.push({
          kind: "act",
          instruction: step.instruction,
          selector: step.selector,
          ...(step.method && step.method !== "click" ? { method: step.method } : {}),
        });
      }
    }
    return out;
  };

  const endSessionOnly = async () => {
    const sid = sessionId;
    if (!sid) return;
    if (recordingIntervalRef.current) {
      clearInterval(recordingIntervalRef.current);
      recordingIntervalRef.current = null;
    }
    if (liveViewRetryRef.current) {
      clearInterval(liveViewRetryRef.current);
      liveViewRetryRef.current = null;
    }
    if (recording && sid) await toggleRecording(sid, false);
    try {
      await fetch(`${getBaseUrl()}/recorder/${sid}/end`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({
          browserbase_session_id: browserbaseSessionId,
          device,
          browser,
        }),
      });
    } catch {
      /* ignore */
    }
    setSessionId(null);
    setBrowserbaseSessionId(null);
    setLiveViewUrl(null);
    setRecording(false);
  };

  const openEndModal = async () => {
    await endSessionOnly();
    setSaveName("");
    setSaveExpectedBehavior("");
    setEndModalOpen(true);
  };

  const handleSaveTest = async () => {
    const name = saveName.trim();
    const expected_behavior = saveExpectedBehavior.trim();
    if (!name) {
      toast({ title: "Name required", description: "Enter a test name.", variant: "destructive" });
      return;
    }
    if (!expected_behavior) {
      toast({ title: "Expected behavior required", description: "Describe what should happen.", variant: "destructive" });
      return;
    }
    const stepsPayload = buildStepsForSave();
    if (stepsPayload.length < 1) {
      toast({
        title: "No steps",
        description: "Record at least one action before saving.",
        variant: "destructive",
      });
      return;
    }
    setSaving(true);
    try {
      const res = await fetch(`${getBaseUrl()}/recorder/save-test`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({
          name,
          expected_behavior,
          url: url.trim(),
          steps: stepsPayload,
        }),
      });
      if (!res.ok) {
        if (res.status === 429) {
          throw new Error("AI Quota Reached. Please try again later.");
        }
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || err.detail || `Save failed: ${res.status}`);
      }
      toast({ title: "Test saved", description: `${name} has been saved.` });
      setSteps([]);
      setUrl("");
      setEndModalOpen(false);
      setSaveName("");
      setSaveExpectedBehavior("");
    } catch (e) {
      toast({
        title: "Save failed",
        description: e instanceof Error ? e.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleCancelEnd = () => {
    setEndModalOpen(false);
    setSteps([]);
    setUrl("");
  };

  return (
    <div className="flex h-[calc(100vh-6rem)] flex-col overflow-hidden rounded-xl border border-zinc-200 bg-zinc-50/80 shadow-sm">
      {/* Toolbar */}
      <div className="flex shrink-0 items-center justify-between gap-4 border-b border-zinc-200 bg-white px-4 py-3">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          {sessionId ? (
            <p className="truncate text-sm text-zinc-500" title={url}>
              {url}
            </p>
          ) : (
            <>
              <Input
                type="url"
                placeholder="https://example.com"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !loading && url.trim() && startSession()}
                className="w-72 max-w-full border-zinc-300 bg-white text-zinc-900 placeholder:text-zinc-400 focus-visible:ring-teal-500"
                disabled={loading}
              />
              <Button
                onClick={startSession}
                disabled={loading || !url.trim()}
                className="shrink-0 bg-teal-600 font-medium text-white hover:bg-teal-700"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Start recording"}
              </Button>
            </>
          )}
          {sessionId && (
            <button
              type="button"
              onClick={() => toggleRecording(sessionId!, !recording)}
              className={cn(
                "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                recording
                  ? "bg-teal-600 text-white hover:bg-teal-700"
                  : "border border-zinc-300 bg-white text-zinc-700 hover:bg-zinc-50"
              )}
            >
              {recording ? (
                <>
                  <CircleDot className="h-4 w-4 animate-pulse" />
                  Recording
                </>
              ) : (
                <>
                  <Circle className="h-4 w-4" />
                  Paused
                </>
              )}
            </button>
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={openEndModal}
          disabled={!sessionId}
          className="shrink-0 border-zinc-300 text-zinc-700 hover:bg-zinc-100"
        >
          <Square className="h-4 w-4 mr-1.5" />
          End session
        </Button>
      </div>

      {/* Save-test modal */}
      <Dialog open={endModalOpen} onOpenChange={(open) => !open && handleCancelEnd()}>
        <DialogContent className="border-zinc-200 bg-white sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-zinc-900">Save test</DialogTitle>
            <DialogDescription className="text-zinc-500">
              Give this recording a name and describe the expected outcome. It will be saved to your tests.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <label className="text-sm font-medium text-zinc-700">Test name</label>
              <Input
                value={saveName}
                onChange={(e) => setSaveName(e.target.value)}
                placeholder="e.g. Login and checkout flow"
                className="border-zinc-300 bg-white text-zinc-900"
              />
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium text-zinc-700">Expected behavior</label>
              <Textarea
                value={saveExpectedBehavior}
                onChange={(e) => setSaveExpectedBehavior(e.target.value)}
                placeholder="What should happen when the test runs?"
                className="min-h-[80px] border-zinc-300 bg-white text-zinc-900"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={handleCancelEnd}
              disabled={saving}
              className="border-zinc-300 text-zinc-700 hover:bg-zinc-100"
            >
              Cancel
            </Button>
            <Button
              onClick={handleSaveTest}
              disabled={saving || !saveName.trim() || !saveExpectedBehavior.trim()}
              className="bg-teal-600 text-white hover:bg-teal-700"
            >
              {saving ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving…
                </>
              ) : (
                "Save test"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Main: steps list + browser */}
      <div className="flex min-h-0 flex-1 overflow-hidden">
        <div className="flex w-80 shrink-0 flex-col border-r border-zinc-200 bg-white">
          <div className="flex items-center gap-2 border-b border-zinc-100 px-4 py-3">
            <Monitor className="h-5 w-5 text-zinc-400" />
            <h2 className="text-sm font-semibold text-zinc-800">Recorded steps</h2>
          </div>
          <div
            ref={stepsListRef}
            className="flex-1 space-y-3 overflow-y-auto p-4"
          >
            {steps.length === 0 ? (
              <div className="rounded-lg border border-dashed border-zinc-200 bg-zinc-50/50 py-10 text-center text-sm text-zinc-500">
                No steps yet. Start recording and interact in the browser.
              </div>
            ) : (
              steps.map((step, i) => (
                <div
                  key={step.id}
                  className="group flex gap-2 rounded-lg border border-zinc-200 bg-zinc-50/50 p-3"
                >
                  <span className="shrink-0 text-xs font-medium text-zinc-400">
                    {i + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-zinc-800">{step.instruction}</p>
                    {step.selector && (
                      <p className="mt-1 truncate font-mono text-xs text-zinc-500">
                        {step.selector}
                      </p>
                    )}
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 shrink-0 opacity-70 hover:opacity-100"
                    onClick={() => removeStep(step.id)}
                    aria-label="Remove step"
                  >
                    <Trash2 className="h-4 w-4 text-zinc-500" />
                  </Button>
                </div>
              ))
            )}
          </div>
        </div>
        <div className="flex flex-1 items-center justify-center bg-zinc-200">
          {liveViewUrl ? (
            <iframe
              src={liveViewUrl}
              sandbox="allow-same-origin allow-scripts"
              allow="clipboard-read; clipboard-write"
              className="h-full w-full min-h-[400px] border-0"
              style={{ pointerEvents: "auto" }}
              title="Live browser view"
            />
          ) : (
            <div className="flex flex-col items-center gap-3 text-zinc-500">
              <Monitor className="h-12 w-12 opacity-50" />
              <p className="text-sm">Loading browser view…</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
