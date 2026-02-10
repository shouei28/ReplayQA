"""Shared state for recorder: in-memory session store and slot release on cleanup."""
import threading
from typing import Any, Dict

from pipeline.services.browser_slot_manager import get_slot_manager

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
