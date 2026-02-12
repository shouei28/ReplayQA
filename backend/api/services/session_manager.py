import os
import uuid
from typing import Dict, Optional, Any
from browserbase import Browserbase
from api.services.lock_manager import acquire_browser_slot, release_browser_slot

def get_client():
    api_key = os.environ.get("BROWSERBASE_API_KEY")
    if not api_key:
        raise ValueError("BROWSERBASE_API_KEY environment variable is not set.")
    return Browserbase(api_key=api_key)

def start_session(url: Optional[str] = None, user_id: str = "system") -> Dict[str, Any]:
    """
    Starts a Browserbase session and returns the URLs needed to connect.
    Does NOT connect Playwright, just reserves the machine.
    """

    """
    Attempts to start a session. 
    Raises Exception if the single slot is busy.
    """
    # 1. Try to acquire the global lock
    session_owner_token = f"{user_id}_{uuid.uuid4()}"
    
    if not acquire_browser_slot(session_owner_token):
        raise  BlockingIOError("Browser slot is busy. Another test or user is currently active.")

    try:
        bb = get_client()
        project_id = os.environ.get("BROWSERBASE_PROJECT_ID")
        
        # 2. Create Browserbase Session
        session = bb.sessions.create(
            project_id=project_id,
            browser_settings={"viewport": {"width": 1280, "height": 720}}
        )

        live_view_url = session.debugger_fullscreen_url
        if live_view_url:
            live_view_url = f"{live_view_url}&navbar=false"

        return {
            "success": True,
            "session_id": session.id,
            "connect_url": session.connect_url,
            "live_view_url": live_view_url,
            "lock_token": session_owner_token
        }

    except Exception as e:
        # Release lock if browserbase session fails
        release_browser_slot(session_owner_token)
        raise e

def end_session(session_id: str) -> bool:
    """
    Ends a Browserbase session by its ID.
    """
    bb = get_client()
    try:
        bb.sessions.update(session_id, status="finished")
        print(f"Session {session_id} marked as completed.")
        return True
    except Exception as e:
        print(f"Error ending session {session_id}: {e}")
        return False

    