"use client";

import { useAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function HomePage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading) {
      router.replace(user ? "/dashboard/overview" : "/login");
    }
  }, [user, isLoading, router]);

  return (
    <main className="min-h-screen flex items-center justify-center bg-slate-950">
      <div className="flex items-center gap-3 text-slate-400">
        <svg
          className="animate-spin w-5 h-5"
          viewBox="0 0 24 24"
          fill="none"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
        Loading…
      </div>
    </main>
  );
}
