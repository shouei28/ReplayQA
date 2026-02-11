"use client";

import * as React from "react";

export type ToastVariant = "default" | "destructive";

export interface Toast {
  id: string;
  title?: string;
  description?: string;
  variant?: ToastVariant;
  action?: React.ReactElement;
}

interface ToastState {
  toasts: Toast[];
}

const ToastContext = React.createContext<{
  toasts: Toast[];
  toast: (props: {
    title?: string;
    description?: string;
    variant?: ToastVariant;
  }) => void;
  dismiss: (id: string) => void;
} | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = React.useState<ToastState>({ toasts: [] });

  const toast = React.useCallback(
    (props: { title?: string; description?: string; variant?: ToastVariant }) => {
      const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      setState((prev) => ({
        toasts: [...prev.toasts, { ...props, id }],
      }));
      setTimeout(() => {
        setState((prev) => ({
          toasts: prev.toasts.filter((t) => t.id !== id),
        }));
      }, 5000);
    },
    []
  );

  const dismiss = React.useCallback((id: string) => {
    setState((prev) => ({
      toasts: prev.toasts.filter((t) => t.id !== id),
    }));
  }, []);

  const value = React.useMemo(
    () => ({ toasts: state.toasts, toast, dismiss }),
    [state.toasts, toast, dismiss]
  );

  return (
    <ToastContext.Provider value={value}>{children}</ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = React.useContext(ToastContext);
  if (!ctx) {
    return {
      toasts: [],
      toast: (props: { title?: string; description?: string; variant?: ToastVariant }) => {
        console.warn("useToast used without ToastProvider", props);
      },
      dismiss: () => {},
    };
  }
  return ctx;
}
