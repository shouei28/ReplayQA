"""Recorder execution: agent(), act(), get recorded actions, toggle recording.
Agent runs in the recording thread (single CDP connection) so the session is not closed.
Act uses a fresh CDP connection from the request thread (short-lived)."""
import base64
import threading
from playwright.sync_api import sync_playwright

from pipeline.services.automation.types import Action
from pipeline.services.automation.actions.executor import perform_action

from . import state

DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
AGENT_WAIT_TIMEOUT = 120  # seconds


def _connect_url(browserbase_session_id: str) -> str:
    return f"wss://connect.browserbase.com/v1/sessions/{browserbase_session_id}"


def _sanitize_for_json(obj):
    """Recursively replace bytes with base64 strings so JSON serialization doesn't fail."""
    if isinstance(obj, bytes):
        return base64.b64encode(obj).decode("ascii")
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(x) for x in obj]
    return obj


def execute_agent(
    session_id: str,
    instruction: str,
    username: str | None = None,
    password: str | None = None,
) -> dict:
    """
    Submit instruction to the recording thread; it runs Pilot.agent() there (single CDP
    connection). Wait for result so we don't open a second connection that would close the session.
    For login steps, pass username/password so the agent can use fill_sensitive_field with credentials.
    """
    credentials = None
    if username is not None or password is not None:
        credentials = {
            "username": (username or "").strip(),
            "password": password or "",
        }
    with state.recording_lock:
        if session_id not in state.recording_sessions:
            return {"error": "Recording session not found", "status": 404}
        rec = state.recording_sessions[session_id]
        if rec.get("page") is None:
            return {"error": "Session has no page yet", "status": 400}
        if rec.get("pending_agent_instruction") is not None:
            return {"error": "Agent already running", "status": 409}
        recording_was_enabled = rec.get("recording_enabled", False)
        rec["recording_enabled"] = False
        event = threading.Event()
        rec["pending_agent_instruction"] = instruction
        rec["pending_agent_credentials"] = credentials
        rec["pending_agent_result"] = None
        rec["pending_agent_event"] = event

    try:
        if not event.wait(timeout=AGENT_WAIT_TIMEOUT):
            with state.recording_lock:
                if session_id in state.recording_sessions:
                    state.recording_sessions[session_id].pop("pending_agent_instruction", None)
                    state.recording_sessions[session_id]["pending_agent_event"] = None
            return {"error": "Agent execution timed out", "status": 504}

        with state.recording_lock:
            if session_id not in state.recording_sessions:
                return {"error": "Session closed during execution", "status": 503}
            d = state.recording_sessions[session_id].pop("pending_agent_result", None)

        if d is None:
            return {"error": "No agent result", "status": 500}

        d = _sanitize_for_json(d)
        message = d.get("message") or d.get("final_message") or ""
        page_closed_indicators = [
            "Target page, context or browser has been closed",
            "Connection closed",
            "Page closed",
        ]
        page_was_closed = any(ind in message for ind in page_closed_indicators)
        if page_was_closed:
            with state.recording_lock:
                if session_id in state.recording_sessions:
                    del state.recording_sessions[session_id]
        return {
            "success": d.get("success", False),
            "result": d,
            "message": message,
            "completed": d.get("completed", False),
            "page_closed": page_was_closed,
        }
    finally:
        with state.recording_lock:
            if session_id in state.recording_sessions:
                state.recording_sessions[session_id]["recording_enabled"] = recording_was_enabled


def execute_act(session_id: str, action: dict) -> dict:
    """Execute a single act via perform_action(). Uses a fresh CDP connection from this thread."""
    with state.recording_lock:
        if session_id not in state.recording_sessions:
            return {"error": "Recording session not found", "status": 404}
        rec = state.recording_sessions[session_id]
        browserbase_session_id = rec.get("browserbase_session_id")
        connect_url = rec.get("connect_url")
        recording_was_enabled = rec.get("recording_enabled", False)
        rec["recording_enabled"] = False
        rec["agent_executing"] = True

    if not browserbase_session_id:
        with state.recording_lock:
            if session_id in state.recording_sessions:
                state.recording_sessions[session_id]["agent_executing"] = False
                if recording_was_enabled:
                    state.recording_sessions[session_id]["recording_enabled"] = True
        return {"error": "Session has no browser connection", "status": 400}

    connect_url = connect_url or _connect_url(browserbase_session_id)
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(connect_url, timeout=15000)
            context = browser.contexts[0] if browser.contexts else None
            if not context:
                return {"error": "No browser context", "status": 500}
            page = context.pages[0] if context.pages else context.new_page()
            act = Action(
                selector=(action.get("selector") or "").strip(),
                description=(action.get("description") or "").strip(),
                method=(action.get("method") or "click").strip().lower(),
                arguments=action.get("arguments") if isinstance(action.get("arguments"), list) else [],
            )
            perform_action(page, act, timeout_ms=30000)
        return {
            "success": True,
            "message": f"Action [{act.method}] performed",
            "result": {"success": True, "message": act.description},
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)[:500],
            "result": {"success": False, "message": str(e)[:500]},
            "error": str(e)[:500],
            "status": 500,
        }
    finally:
        with state.recording_lock:
            if session_id in state.recording_sessions:
                state.recording_sessions[session_id]["agent_executing"] = False
                if recording_was_enabled:
                    state.recording_sessions[session_id]["recording_enabled"] = True


def get_recorded_actions(session_id: str) -> dict:
    """Return queued actions and clear queue. Includes session_closed=True if session not found."""
    with state.recording_lock:
        if session_id not in state.recording_sessions:
            return {"success": True, "actions": [], "recording": False, "session_closed": True}
        session_data = state.recording_sessions[session_id]
        actions = session_data.get("actions_queue", [])
        session_data["actions_queue"] = []
        return {
            "success": True,
            "actions": actions,
            "recording": session_data.get("recording_enabled", False),
            "session_closed": False,
        }


def toggle_recording(session_id: str, enabled: bool) -> dict:
    """Set recording_enabled for session. Returns dict with success, enabled, message or error and status."""
    with state.recording_lock:
        if session_id not in state.recording_sessions:
            return {"error": "Recording session not found", "status": 404}
        state.recording_sessions[session_id]["recording_enabled"] = enabled
    return {
        "success": True,
        "enabled": enabled,
        "message": f"Recording {'enabled' if enabled else 'disabled'}",
    }
