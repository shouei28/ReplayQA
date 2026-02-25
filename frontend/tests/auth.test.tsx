/**
 * Tests for the AuthProvider and useAuth hook (lib/auth.tsx).
 */
import React from "react";
import { render, screen, act, waitFor } from "@testing-library/react";

// We need to mock next/navigation before importing AuthProvider
jest.mock("next/navigation", () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
  }),
}));

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

import { AuthProvider, useAuth } from "@/lib/auth";

// Helper component that exposes auth context values for testing
function AuthConsumer() {
  const { user, token, isLoading, login, logout } = useAuth();
  return (
    <div>
      <span data-testid="loading">{String(isLoading)}</span>
      <span data-testid="user">{user ? user.username : "none"}</span>
      <span data-testid="token">{token ?? "none"}</span>
      <button data-testid="login-btn" onClick={() => login("testuser", "pass123")}>
        Login
      </button>
      <button data-testid="logout-btn" onClick={logout}>
        Logout
      </button>
    </div>
  );
}

describe("useAuth", () => {
  it("throws when used outside AuthProvider", () => {
    // Suppress console.error for expected error
    const spy = jest.spyOn(console, "error").mockImplementation(() => {});
    expect(() => {
      render(<AuthConsumer />);
    }).toThrow("useAuth must be used within AuthProvider");
    spy.mockRestore();
  });
});

describe("AuthProvider", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    localStorageMock.clear();
  });

  it("initializes with no user when no stored token", async () => {
    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });
    expect(screen.getByTestId("user").textContent).toBe("none");
    expect(screen.getByTestId("token").textContent).toBe("none");
  });

  it("hydrates user from stored access token on mount", async () => {
    localStorageMock.setItem("access_token", "stored-token");
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: "u1", username: "hydrated", email: "h@e.com" }),
    });

    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("user").textContent).toBe("hydrated");
    });
  });

  it("clears tokens when stored token is invalid and refresh fails", async () => {
    localStorageMock.setItem("access_token", "bad-token");
    // First fetch (apiFetchMe) fails
    mockFetch.mockResolvedValueOnce({ ok: false, status: 401 });
    // Refresh also fails (no refresh token set)

    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });
    expect(screen.getByTestId("user").textContent).toBe("none");
    expect(localStorageMock.removeItem).toHaveBeenCalledWith("access_token");
  });

  it("logout clears user and tokens", async () => {
    // Start authenticated
    localStorageMock.setItem("access_token", "valid-token");
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: "u1", username: "testuser", email: "t@e.com" }),
    });

    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("user").textContent).toBe("testuser");
    });

    // Click logout
    act(() => {
      screen.getByTestId("logout-btn").click();
    });

    expect(screen.getByTestId("user").textContent).toBe("none");
    expect(screen.getByTestId("token").textContent).toBe("none");
    expect(localStorageMock.removeItem).toHaveBeenCalledWith("access_token");
    expect(localStorageMock.removeItem).toHaveBeenCalledWith("refresh_token");
  });
});
