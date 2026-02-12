"""
Recorder service layer: session lifecycle, recording thread, get actions, toggle recording.
Views in api.views.recorder call these; business logic lives here.
"""

from .recording_service import start_recording
from .session_service import end_session, get_live_view_url, start_session
from .state import (
    get_recorded_actions,
    recording_lock,
    recording_sessions,
    release_slot_and_remove_session,
    toggle_recording,
)
from .summarize_steps import summarize_steps

__all__ = [
    "summarize_steps",
    "recording_sessions",
    "recording_lock",
    "release_slot_and_remove_session",
    "start_session",
    "end_session",
    "get_live_view_url",
    "start_recording",
    "get_recorded_actions",
    "toggle_recording",
]
