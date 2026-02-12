"""
Recorder service layer: session lifecycle, recording thread, get actions, toggle recording.
Views in api.views.recorder call these; business logic lives here.
"""
from .summarize_steps import summarize_steps
from .state import (
    recording_sessions,
    recording_lock,
    release_slot_and_remove_session,
    get_recorded_actions,
    toggle_recording,
)
from .session_service import start_session, end_session, get_live_view_url
from .recording_service import start_recording

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
