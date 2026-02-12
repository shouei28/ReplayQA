"""
URL routing for API endpoints
"""

from django.urls import path

from .views import (
    admin_management, auth_logout, delete_test_result, get_auth_me, get_live_view,
    get_screenshot, get_test_results, get_test_status, health_check, list_tests,
    run_pipeline, saved_test_detail, saved_tests_list_create,
)
from .views.recorder import (
    RecorderEndView, RecorderGetRecordedActionsView, RecorderLiveViewView,
    RecorderSaveTestView, RecorderStartRecordingView, RecorderStartView,
    RecorderToggleRecordingView,
)

urlpatterns = [
    # Health check
    path("health", health_check, name="health"),
    # Pipeline Execution
    path("run-pipeline", run_pipeline, name="run-pipeline"),
    path("status/<uuid:test_execution_id>", get_test_status, name="test-status"),
    path("results/<uuid:test_execution_id>", get_test_results, name="test-results"),
    # Test History
    path("tests", list_tests, name="list-tests"),
    path("<uuid:test_result_id>", delete_test_result, name="delete-test-result"),
    # Saved Tests
    path("saved-tests", saved_tests_list_create, name="saved-tests-list-create"),
    path("saved-tests/<uuid:test_id>", saved_test_detail, name="saved-test-detail"),
    # Screenshots
    path(
        "screenshot/<uuid:test_result_id>/<int:step_num>",
        get_screenshot,
        name="get-screenshot",
    ),
    # Authentication
    path("auth/me", get_auth_me, name="auth-me"),
    path("auth/logout", auth_logout, name="auth-logout"),
    # Admin
    path("admin", admin_management, name="admin-management"),
    # Live View
    path("live-view/<uuid:test_execution_id>/", get_live_view, name="live-view"),
    # Recorder endpoints (simple recorder, no agent execution)
    path("recorder/start", RecorderStartView.as_view(), name="recorder-start"),
    path(
        "recorder/<str:session_id>/live-view",
        RecorderLiveViewView.as_view(),
        name="recorder-live-view",
    ),
    path(
        "recorder/<str:session_id>/start-recording",
        RecorderStartRecordingView.as_view(),
        name="recorder-start-recording",
    ),
    path(
        "recorder/<str:session_id>/toggle-recording",
        RecorderToggleRecordingView.as_view(),
        name="recorder-toggle-recording",
    ),
    path(
        "recorder/<str:session_id>/recorded-actions",
        RecorderGetRecordedActionsView.as_view(),
        name="recorder-recorded-actions",
    ),
    path(
        "recorder/<str:session_id>/end", RecorderEndView.as_view(), name="recorder-end"
    ),
    path(
        "recorder/save-test", RecorderSaveTestView.as_view(), name="recorder-save-test"
    ),
]
