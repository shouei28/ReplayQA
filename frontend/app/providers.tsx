"use client";

import type { ReactNode } from "react";
import { AuthProvider } from "@/lib/auth";
import { ToastProvider } from "@/hooks/use-toast";
import { Toaster } from "@/components/ui/toaster";

export function Providers({ children }: { children: ReactNode }) {
    return (
        <AuthProvider>
            <ToastProvider>
                {children}
                <Toaster />
            </ToastProvider>
        </AuthProvider>
    );
}
