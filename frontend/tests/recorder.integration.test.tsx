/**
 * Integration tests for the Recorder page.
 * Tests the Recorder component with its UI elements and user flows.
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Recorder } from "@/components/recorder";
import { ToastProvider } from "@/hooks/use-toast";
import { Toaster } from "@/components/ui/toaster";

function renderRecorder() {
  return render(
    <ToastProvider>
      <Recorder />
      <Toaster />
    </ToastProvider>
  );
}

describe("Recorder integration", () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("renders initial UI with URL input, Start button, and Recorded steps section", () => {
    renderRecorder();

    expect(screen.getByPlaceholderText(/https:\/\/example\.com/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /start recording/i })).toBeInTheDocument();
    expect(screen.getByText(/recorded steps/i)).toBeInTheDocument();
    expect(screen.getByText(/no steps yet/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /end session/i })).toBeInTheDocument();
  });

  it("disables Start button when URL is empty", () => {
    renderRecorder();

    const startBtn = screen.getByRole("button", { name: /start recording/i });
    expect(startBtn).toBeDisabled();
  });

  it("enables Start button when URL is entered", () => {
    renderRecorder();

    const input = screen.getByPlaceholderText(/https:\/\/example\.com/i);
    fireEvent.change(input, { target: { value: "https://example.com" } });

    const startBtn = screen.getByRole("button", { name: /start recording/i });
    expect(startBtn).not.toBeDisabled();
  });

  it("shows session UI after successful start", async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          session_id: "test-session",
          browserbase_session_id: "bb-123",
          live_view_url: "https://live.example.com",
          connect_url: "wss://connect.example.com",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ live_view_url: "https://live.example.com" }),
      })
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValue({ ok: true, json: async () => ({ actions: [] }) });

    renderRecorder();

    const input = screen.getByPlaceholderText(/https:\/\/example\.com/i);
    fireEvent.change(input, { target: { value: "https://example.com" } });

    const startBtn = screen.getByRole("button", { name: /start recording/i });
    fireEvent.click(startBtn);

    await waitFor(() => {
      expect(screen.getByText("https://example.com")).toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: /recording/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /end session/i })).not.toBeDisabled();
  });
});
