"""Recorder session lifecycle: Browserbase session, end, live view URL.
Initial navigation is done by the recording thread when it connects (single CDP connection)."""
import os
import time

from services.browser_slot_manager import get_slot_manager
from . import state


def start_session(url: str, device: str = "desktop", browser: str = "chrome") -> dict:
    """
    Create Browserbase session only. Do not connect here—connecting and disconnecting
    would tear down the session (410 Gone). The recording thread connects once and
    navigates to url via start_recording(..., initial_url=url).
    Returns session info dict. session_id is the Browserbase session id.
    """
    browserbase_api_key = os.environ.get("BROWSERBASE_API_KEY")
    browserbase_project_id = os.environ.get("BROWSERBASE_PROJECT_ID")

    if not browserbase_api_key or not browserbase_project_id:
        raise ValueError("Missing required environment variables (BROWSERBASE_API_KEY, BROWSERBASE_PROJECT_ID)")

    slot_manager = get_slot_manager()
    slot_manager.acquire_slot(device, browser)

    viewport = {"width": 1280, "height": 720}
    if device == "mobile":
        viewport = {"width": 375, "height": 667}

    try:
        session = slot_manager.create_session_with_retry(
            project_id=browserbase_project_id,
            browser_settings={"viewport": viewport},
            device=device,
            browser=browser,
        )
        browserbase_session_id = session.id
        connect_url = session.connect_url
        live_view_url = get_live_view_url(browserbase_session_id)

        return {
            "success": True,
            "session_id": browserbase_session_id,
            "browserbase_session_id": browserbase_session_id,
            "live_view_url": live_view_url,
            "connect_url": connect_url,
            "device": device,
            "browser": browser,
        }
    except Exception:
        slot_manager.release_slot(device, browser)
        raise


def end_session(
    session_id: str,
    browserbase_session_id: str | None,
    device: str = "desktop",
    browser: str = "chrome",
) -> None:
    """Remove recording session (stops polling loop) and release slot."""
    with state.recording_lock:
        if session_id in state.recording_sessions:
            state.recording_sessions[session_id]["recording_enabled"] = False
            del state.recording_sessions[session_id]
            print(f"[RECORDER] Deleted session {session_id} - polling loop will exit")
    time.sleep(0.5)

    if browserbase_session_id:
        get_slot_manager().release_slot(device, browser)


def get_live_view_url(browserbase_session_id: str) -> str | None:
    """Return Browserbase debugger fullscreen URL for live view, or None."""
    browserbase_api_key = os.environ.get("BROWSERBASE_API_KEY")
    if not browserbase_api_key:
        return None
    from browserbase import Browserbase
    bb = Browserbase(api_key=browserbase_api_key)
    live_view_links = bb.sessions.debug(browserbase_session_id)
    live_view_url = live_view_links.debuggerFullscreenUrl
    if live_view_url:
        live_view_url = f"{live_view_url}&navbar=false"
    return live_view_url
