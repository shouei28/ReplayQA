"""
Recorder service layer: session lifecycle, recording thread, and Pilot execution.
Views in pipeline.views.recorder call these; business logic lives here.
"""
from .summarize_steps import steps_to_text, summarize_steps
from .state import recording_sessions, recording_lock, release_slot_and_remove_session
from .session_service import start_session, end_session, get_live_view_url
from .recording_service import start_recording
from .execution_service import execute_agent, execute_act, get_recorded_actions, toggle_recording

__all__ = [
    "steps_to_text",
    "summarize_steps",
    "recording_sessions",
    "recording_lock",
    "release_slot_and_remove_session",
    "start_session",
    "end_session",
    "get_live_view_url",
    "start_recording",
    "execute_agent",
    "execute_act",
    "get_recorded_actions",
    "toggle_recording",
]
