/**
 * API client for ReplayQA backend.
 * Base URL should be set via NEXT_PUBLIC_API_URL or default to localhost.
 */

import type { Test, TestExecution, TestResult } from "./types";

const getBaseUrl = () =>
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api")
    : process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api";

function authHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${getBaseUrl().replace(/\/$/, "")}/${path.replace(/^\//, "")}`;
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("access_token")
      : null;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json() as Promise<T>;
}

/* ------------------------------------------------------------------ */
/*  Recorder API                                                       */
/* ------------------------------------------------------------------ */

export const recorderApi = {
  start: (body: { url: string; device?: string; browser?: string }) =>
    apiFetch<{ session_id: string; connect_url: string; live_view_url: string }>(
      "recorder/start",
      { method: "POST", body: JSON.stringify(body) }
    ),
  startRecording: (
    sessionId: string,
    body: { browserbase_session_id: string; connect_url?: string; url?: string }
  ) =>
    apiFetch<{ success: boolean }>(
      `recorder/${sessionId}/start-recording`,
      { method: "POST", body: JSON.stringify(body) }
    ),
  getRecordedActions: (sessionId: string) =>
    apiFetch<{ actions: unknown[]; recording: boolean; session_closed: boolean }>(
      `recorder/${sessionId}/recorded-actions`
    ),
  toggleRecording: (sessionId: string, enabled: boolean) =>
    apiFetch<{ success: boolean; enabled: boolean }>(
      `recorder/${sessionId}/toggle-recording`,
      { method: "POST", body: JSON.stringify({ enabled }) }
    ),
  end: (sessionId: string, body: { browserbase_session_id: string }) =>
    apiFetch<{ success: boolean }>(`recorder/${sessionId}/end`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  saveTest: (body: {
    test_name: string;
    description?: string;
    url: string;
    steps: unknown[];
    expected_behavior?: string;
  }) =>
    apiFetch<{ success: boolean; test_id: string }>("recorder/save-test", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

/* ------------------------------------------------------------------ */
/*  Saved Tests API                                                    */
/* ------------------------------------------------------------------ */

export const testsApi = {
  list: () => apiFetch<Test[]>("saved-tests"),

  get: (id: string) => apiFetch<Test>(`saved-tests/${id}`),

  create: (body: {
    test_name: string;
    description?: string;
    url: string;
    steps: unknown[];
    expected_behavior?: string;
  }) =>
    apiFetch<Test>("saved-tests", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  update: (id: string, body: Partial<Test>) =>
    apiFetch<Test>(`saved-tests/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  delete: (id: string) =>
    apiFetch<void>(`saved-tests/${id}`, { method: "DELETE" }),
};

/* ------------------------------------------------------------------ */
/*  Pipeline / Execution API                                           */
/* ------------------------------------------------------------------ */

export const pipelineApi = {
  run: (body: {
    url: string;
    description: string;
    steps: unknown[];
    expected_behavior?: string;
    test_id?: string;
    test_name?: string;
  }) =>
    apiFetch<{ job_id: string; message: string; status: string }>(
      "run-pipeline",
      { method: "POST", body: JSON.stringify(body) }
    ),

  status: (executionId: string) =>
    apiFetch<TestExecution>(`status/${executionId}`),

  results: (executionId: string) =>
    apiFetch<TestResult>(`results/${executionId}`),

  liveView: (executionId: string) =>
    apiFetch<{
      live_view_url: string;
      session_id: string;
      device: string;
      browser: string;
    }>(`live-view/${executionId}/`),
};

/* ------------------------------------------------------------------ */
/*  Execution History API                                              */
/* ------------------------------------------------------------------ */

export const executionsApi = {
  list: () =>
    apiFetch<{ results: TestExecution[] }>("tests"),

  delete: (id: string) =>
    apiFetch<void>(`${id}`, { method: "DELETE" }),
};

/* ------------------------------------------------------------------ */
/*  Schedules API (django-celery-beat)                                 */
/* ------------------------------------------------------------------ */

export interface ScheduleResponse {
  id: string;
  test_id: string;
  test_name: string;
  schedule_type: "weekly" | "once" | "daily" | "custom";
  run_on_days: number[];
  run_on_date: string;
  run_at: string;
  repeat_every: number;
  repeat_unit: string;
  name: string;
  last_run_at: string | null;
  enabled: boolean;
}

export const schedulesApi = {
  list: () => apiFetch<ScheduleResponse[]>("schedules"),

  create: (body: {
    test_id: string;
    schedule_type: "weekly" | "once" | "daily" | "custom";
    run_on_days?: number[];
    run_on_date?: string;
    run_at?: string;
    starts_on?: string;
    repeat_every?: number;
    repeat_unit?: string;
    name?: string;
  }) =>
    apiFetch<{ detail: string; schedule_type: string }>("schedules", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  delete: async (id: string): Promise<void> => {
    const url = `${getBaseUrl().replace(/\/$/, "")}/schedules/${id}`;
    const token =
      typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    const res = await fetch(url, {
      method: "DELETE",
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    if (res.status === 204) return;
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error((data as { detail?: string })?.detail || `Delete failed: ${res.status}`);
    }
  },
};
