/**
 * API client for ReplayQA backend.
 * Base URL should be set via NEXT_PUBLIC_API_URL or default to localhost.
 */

const getBaseUrl = () =>
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api")
    : process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api";

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
