/**
 * Tests for the ToastProvider and useToast hook (hooks/use-toast.tsx).
 */
import React from "react";
import { render, screen, act } from "@testing-library/react";
import { ToastProvider, useToast } from "@/hooks/use-toast";

// Helper component to expose toast context for testing
function ToastConsumer() {
  const { toasts, toast, dismiss } = useToast();
  return (
    <div>
      <span data-testid="count">{toasts.length}</span>
      <ul>
        {toasts.map((t) => (
          <li key={t.id} data-testid={`toast-${t.id}`}>
            {t.title}
            <button data-testid={`dismiss-${t.id}`} onClick={() => dismiss(t.id)}>
              Dismiss
            </button>
          </li>
        ))}
      </ul>
      <button
        data-testid="add-toast"
        onClick={() => toast({ title: "Test Toast", description: "Description" })}
      >
        Add
      </button>
      <button
        data-testid="add-destructive"
        onClick={() =>
          toast({ title: "Error", variant: "destructive" })
        }
      >
        Add Error
      </button>
    </div>
  );
}

describe("useToast outside provider", () => {
  it("returns no-op fallback without throwing", () => {
    // useToast returns a fallback when used without ToastProvider
    const spy = jest.spyOn(console, "warn").mockImplementation(() => {});

    render(<ToastConsumer />);

    expect(screen.getByTestId("count").textContent).toBe("0");

    // Clicking add should not throw, just warn
    act(() => {
      screen.getByTestId("add-toast").click();
    });

    expect(spy).toHaveBeenCalledWith(
      "useToast used without ToastProvider",
      expect.any(Object)
    );
    spy.mockRestore();
  });
});

describe("ToastProvider", () => {
  it("starts with no toasts", () => {
    render(
      <ToastProvider>
        <ToastConsumer />
      </ToastProvider>
    );

    expect(screen.getByTestId("count").textContent).toBe("0");
  });

  it("adds a toast when toast() is called", () => {
    render(
      <ToastProvider>
        <ToastConsumer />
      </ToastProvider>
    );

    act(() => {
      screen.getByTestId("add-toast").click();
    });

    expect(screen.getByTestId("count").textContent).toBe("1");
    expect(screen.getByText("Test Toast")).toBeInTheDocument();
  });

  it("dismiss removes the toast", () => {
    render(
      <ToastProvider>
        <ToastConsumer />
      </ToastProvider>
    );

    act(() => {
      screen.getByTestId("add-toast").click();
    });

    expect(screen.getByTestId("count").textContent).toBe("1");

    // Find the dismiss button and click it
    const toastElements = screen.getAllByRole("button", { name: /dismiss/i });
    act(() => {
      toastElements[0].click();
    });

    expect(screen.getByTestId("count").textContent).toBe("0");
  });

  it("can add multiple toasts", () => {
    render(
      <ToastProvider>
        <ToastConsumer />
      </ToastProvider>
    );

    act(() => {
      screen.getByTestId("add-toast").click();
      screen.getByTestId("add-destructive").click();
    });

    expect(screen.getByTestId("count").textContent).toBe("2");
    expect(screen.getByText("Test Toast")).toBeInTheDocument();
    expect(screen.getByText("Error")).toBeInTheDocument();
  });
});
