"""Shared state for recorder: in-memory session store and slot release on cleanup."""
import threading
from typing import Any, Dict

from services.browser_slot_manager import get_slot_manager

# {session_id: {playwright, page, recording_enabled, actions_queue, device, slot_browser, ...}}
recording_sessions: Dict[str, Dict[str, Any]] = {}
recording_lock = threading.Lock()


def release_slot_and_remove_session(session_id: str) -> None:
    """Remove session from recording_sessions and release its Browserbase slot (e.g. on timeout/errors)."""
    with recording_lock:
        if session_id not in recording_sessions:
            return
        session_data = recording_sessions[session_id]
        device = session_data.get("device", "desktop")
        slot_browser = session_data.get("slot_browser", "chrome")
        del recording_sessions[session_id]
    try:
        get_slot_manager().release_slot(device, slot_browser)
        print(f"[RECORDER] Released slot for session {session_id} (device={device}, browser={slot_browser})")
    except Exception as ex:
        print(f"[RECORDER] Failed to release slot after cleanup: {ex}")


def get_recorded_actions(session_id: str) -> dict:
    """Return queued actions and clear queue. Includes session_closed=True if session not found."""
    with recording_lock:
        if session_id not in recording_sessions:
            return {"success": True, "actions": [], "recording": False, "session_closed": True}
        session_data = recording_sessions[session_id]
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
    with recording_lock:
        if session_id not in recording_sessions:
            return {"error": "Recording session not found", "status": 404}
        recording_sessions[session_id]["recording_enabled"] = enabled
    return {
        "success": True,
        "enabled": enabled,
        "message": f"Recording {'enabled' if enabled else 'disabled'}",
    }
