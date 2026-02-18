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
      // ...authHeaders(),
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
};

/* ------------------------------------------------------------------ */
/*  Saved Tests API                                                    */
/* ------------------------------------------------------------------ */

export const testsApi = {
  list: () => apiFetch<{ results: Test[] }>("tests/"),

  get: (id: string) => apiFetch<Test>(`tests/${id}/`),

  delete: (id: string) =>
    apiFetch<void>(`tests/${id}/`, { method: "DELETE" }),
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
      "pipeline/run-pipeline",
      { method: "POST", body: JSON.stringify(body) }
    ),

  status: (executionId: string) =>
    apiFetch<TestExecution>(`pipeline/status/${executionId}`),

  results: (executionId: string) =>
    apiFetch<TestResult>(`pipeline/results/${executionId}`),

  liveView: (executionId: string) =>
    apiFetch<{
      live_view_url: string;
      session_id: string;
      device: string;
      browser: string;
    }>(`pipeline/live-view/${executionId}/`),
};

/* ------------------------------------------------------------------ */
/*  Execution History API                                              */
/* ------------------------------------------------------------------ */

export const executionsApi = {
  list: () =>
    apiFetch<{ results: TestExecution[] }>("executions/"),
};
