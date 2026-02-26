/**
 * Unit tests for the API client (lib/api.ts).
 * Verifies URL construction, auth headers, error handling, and API method calls.
 */

// We need to mock fetch globally before importing the module
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: jest.fn((key: string) => store[key] ?? null),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    }),
  };
})();
Object.defineProperty(window, "localStorage", { value: localStorageMock });

import { apiFetch, recorderApi, testsApi, pipelineApi, executionsApi } from "@/lib/api";

describe("apiFetch", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    localStorageMock.clear();
  });

  it("constructs the correct URL from the path", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ data: "ok" }),
    });

    await apiFetch("health");

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const calledUrl = mockFetch.mock.calls[0][0] as string;
    expect(calledUrl).toContain("/health");
  });

  it("includes Authorization header when token is in localStorage", async () => {
    localStorageMock.setItem("access_token", "my-jwt-token");
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });

    await apiFetch("some-path");

    const headers = mockFetch.mock.calls[0][1]?.headers as Record<string, string>;
    expect(headers["Authorization"]).toBe("Bearer my-jwt-token");
  });

  it("does not include Authorization header when no token", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });

    await apiFetch("some-path");

    const headers = mockFetch.mock.calls[0][1]?.headers as Record<string, string>;
    expect(headers["Authorization"]).toBeUndefined();
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
    });

    await expect(apiFetch("fail")).rejects.toThrow("API error: 500");
  });

  it("includes Content-Type: application/json", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });

    await apiFetch("test");

    const headers = mockFetch.mock.calls[0][1]?.headers as Record<string, string>;
    expect(headers["Content-Type"]).toBe("application/json");
  });
});

describe("recorderApi", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    localStorageMock.clear();
  });

  it("start sends POST with url in body", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ session_id: "s1", connect_url: "ws://c", live_view_url: "https://l" }),
    });

    await recorderApi.start({ url: "https://example.com" });

    const [, options] = mockFetch.mock.calls[0];
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({ url: "https://example.com" });
  });

  it("getRecordedActions sends GET", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ actions: [], recording: false, session_closed: false }),
    });

    await recorderApi.getRecordedActions("sess-1");

    const calledUrl = mockFetch.mock.calls[0][0] as string;
    expect(calledUrl).toContain("recorder/sess-1/recorded-actions");
  });
});

describe("testsApi", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    localStorageMock.clear();
  });

  it("list sends GET to saved-tests", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ([]),
    });

    await testsApi.list();

    const calledUrl = mockFetch.mock.calls[0][0] as string;
    expect(calledUrl).toContain("saved-tests");
  });

  it("delete sends DELETE", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => undefined,
    });

    await testsApi.delete("abc-123");

    const [, options] = mockFetch.mock.calls[0];
    expect(options.method).toBe("DELETE");
  });
});

describe("pipelineApi", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    localStorageMock.clear();
  });

  it("run sends POST with body", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ job_id: "j1", message: "ok", status: "completed" }),
    });

    const body = {
      url: "https://example.com",
      description: "Test",
      steps: [{ type: "goto" }],
    };
    await pipelineApi.run(body);

    const [, options] = mockFetch.mock.calls[0];
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual(body);
  });

  it("status sends GET", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: "e1", status: "pending" }),
    });

    await pipelineApi.status("exec-1");

    const calledUrl = mockFetch.mock.calls[0][0] as string;
    expect(calledUrl).toContain("status/exec-1");
  });
});

describe("executionsApi", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    localStorageMock.clear();
  });

  it("list sends GET to tests endpoint", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ results: [] }),
    });

    await executionsApi.list();

    const calledUrl = mockFetch.mock.calls[0][0] as string;
    expect(calledUrl).toContain("/tests");
  });

  it("delete sends DELETE with id in path", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => undefined,
    });

    await executionsApi.delete("exec-123");

    const [url, options] = mockFetch.mock.calls[0];
    expect(options.method).toBe("DELETE");
    expect(url).toContain("exec-123");
  });
});
