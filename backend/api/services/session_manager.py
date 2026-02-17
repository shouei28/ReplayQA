import os
import uuid
from typing import Dict, Any
from browserbase import Browserbase
from api.services.lock_manager import acquire_browser_slot, release_browser_slot


def get_client():
    api_key = os.environ.get("BROWSERBASE_API_KEY")
    if not api_key:
        raise ValueError("BROWSERBASE_API_KEY environment variable is not set.")
    return Browserbase(api_key=api_key)


def start_session(user_id: str = "system") -> Dict[str, Any]:
    """
    1. Checks Lock.
    2. If free, creates Browserbase session.
    3. Returns Session ID + Lock Token.
    """
    session_user_token = f"{user_id}_{uuid.uuid4()}"

    # Check if we can run
    if not acquire_browser_slot(session_user_token):
        raise BlockingIOError("System busy. Browser is in use.")

    try:
        # Get client and create session if lock acquired
        bb = get_client()
        session = bb.sessions.create(
            project_id=os.environ.get("BROWSERBASE_PROJECT_ID")
        )
        sess_id = session.id
        live_view = f"https://www.browserbase.com/sessions/{sess_id}"
        connect_url = session.connect_url

        return {
            "session_id": sess_id,
            "connect_url": connect_url,
            "live_view_url": live_view,
            "lock_token": session_user_token,
        }

    except Exception as e:
        release_browser_slot(session_user_token)
        raise e


def end_session(session_id: str, lock_token: str):
    """
    Closes session AND releases the lock.
    """
    bb = get_client()
    try:
        project_id = os.environ.get("BROWSERBASE_PROJECT_ID")
        bb.sessions.update(session_id, project_id=project_id, status="REQUEST_RELEASE")

        print(f"Session {session_id} release requested.")
    except Exception as e:
        print(f"Warning: Failed to close session {session_id}: {e}")
    finally:
        release_browser_slot(lock_token)
