"use client";

import {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useState,
} from "react";
import type { ReactNode } from "react";
import { useRouter } from "next/navigation";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface AuthUser {
    id: string;
    username: string;
    email: string;
}

interface AuthContextValue {
    user: AuthUser | null;
    token: string | null;
    isLoading: boolean;
    login: (username: string, password: string) => Promise<void>;
    register: (
        username: string,
        email: string,
        password: string
    ) => Promise<void>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const API_BASE =
    process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api";

async function apiPost<T>(path: string, body: Record<string, unknown>): Promise<T> {
    const res = await fetch(`${API_BASE}/${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) {
        const msg =
            data?.detail ??
            (data?.errors
                ? Object.values(data.errors).join(" ")
                : `Request failed (${res.status})`);
        throw new Error(msg);
    }
    return data as T;
}

async function apiFetchMe(token: string): Promise<AuthUser> {
    const res = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("Session expired");
    return res.json() as Promise<AuthUser>;
}

/** Try to refresh the access token using the stored refresh token */
async function tryRefreshToken(): Promise<string | null> {
    const refresh = localStorage.getItem("refresh_token");
    if (!refresh) return null;
    try {
        const res = await fetch(`${API_BASE}/auth/refresh`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh }),
        });
        if (!res.ok) return null;
        const data = await res.json();
        const newAccess = data.access as string;
        localStorage.setItem("access_token", newAccess);
        // If rotated, save new refresh token too
        if (data.refresh) {
            localStorage.setItem("refresh_token", data.refresh);
        }
        return newAccess;
    } catch {
        return null;
    }
}

/* ------------------------------------------------------------------ */
/*  Provider                                                           */
/* ------------------------------------------------------------------ */

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<AuthUser | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const router = useRouter();

    /* hydrate from localStorage on mount */
    useEffect(() => {
        const stored = localStorage.getItem("access_token");
        if (!stored) {
            setIsLoading(false);
            return;
        }

        // Try the stored access token first, then refresh if it fails
        apiFetchMe(stored)
            .then((u) => {
                setUser(u);
                setToken(stored);
            })
            .catch(async () => {
                // Access token expired — try refreshing
                const newToken = await tryRefreshToken();
                if (newToken) {
                    try {
                        const u = await apiFetchMe(newToken);
                        setUser(u);
                        setToken(newToken);
                        return;
                    } catch {
                        // Refresh token also invalid
                    }
                }
                // Both tokens invalid — clear and redirect
                localStorage.removeItem("access_token");
                localStorage.removeItem("refresh_token");
            })
            .finally(() => setIsLoading(false));
    }, []);

    const login = useCallback(
        async (username: string, password: string) => {
            const data = await apiPost<{ access: string; refresh: string }>(
                "auth/login",
                { username, password }
            );
            localStorage.setItem("access_token", data.access);
            localStorage.setItem("refresh_token", data.refresh);
            setToken(data.access);
            const me = await apiFetchMe(data.access);
            setUser(me);
            router.push("/dashboard/overview");
        },
        [router]
    );

    const register = useCallback(
        async (username: string, email: string, password: string) => {
            const data = await apiPost<{
                access: string;
                refresh: string;
                user: AuthUser;
            }>("auth/register", { username, email, password });
            localStorage.setItem("access_token", data.access);
            localStorage.setItem("refresh_token", data.refresh);
            setToken(data.access);
            setUser(data.user);
            router.push("/dashboard/overview");
        },
        [router]
    );

    const logout = useCallback(() => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        setUser(null);
        setToken(null);
        router.push("/login");
    }, [router]);

    const value = useMemo<AuthContextValue>(
        () => ({ user, token, isLoading, login, register, logout }),
        [user, token, isLoading, login, register, logout]
    );

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/* ------------------------------------------------------------------ */
/*  Hook                                                               */
/* ------------------------------------------------------------------ */

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error("useAuth must be used within AuthProvider");
    return ctx;
}
