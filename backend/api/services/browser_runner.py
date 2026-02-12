import os
import time
from typing import Dict, Optional, Any
from browserbase import Browserbase

def get_client():
    api_key = os.environ.get("BROWSERBASE_API_KEY")
    if not api_key:
        raise ValueError("BROWSERBASE_API_KEY environment variable is not set.")
    return Browserbase(api_key=api_key)

def start_session(url: Optional[str] = None, device: str = "desktop") -> Dict[str, Any]:
    """
    Starts a Browserbase session and returns the URLs needed to connect.
    Does NOT connect Playwright, just reserves the machine.
    """

    bb = get_client()
    project_id = os.environ.get("BROWSERBASE_PROJECT_ID")

    if not project_id:
        raise ValueError("BROWSERBASE_PROJECT_ID environment variable is not set.")
    
    # Define our viewpoint based on the device type
    viewpoint = {"width": 1280, "height": 720}
    
    # Create our session
    print(f"Creating Browserbase session...")
    session = bb.sessions.create(
        project_id=project_id,
        browser_settings={"viewpoint": viewpoint}
    )

    # Get our "Live View" so users can watch the test/recording
    live_view_url = session.debugger_fullscreen_url
    if live_view_url:
        live_view_url = f"{live_view_url}&navbar=false"

    return {
        "success": True,
        "session_id": session.id,
        "connect_url": session.connect_url,
        "live_view_url": live_view_url,
        "initial_url": url
    }

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

    