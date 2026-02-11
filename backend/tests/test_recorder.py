"""
Tests for recorder API views.
"""
import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient
from rest_framework import status

from core.models import User


@pytest.mark.django_db
class TestRecorderStartView:
    """Tests for POST /api/recorder/start"""

    def test_start_missing_url_returns_400(self):
        """Missing required 'url' returns 400 Bad Request."""
        client = APIClient()
        response = client.post("/api/recorder/start", {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "URL is required"

    def test_start_with_url_success(self):
        """With valid url, returns 200 and session data (mocked start_session)."""
        mock_data = {
            "success": True,
            "session_id": "test-session-123",
            "browserbase_session_id": "test-session-123",
            "live_view_url": "https://example.com/live",
            "connect_url": "wss://example.com/connect",
            "device": "desktop",
            "browser": "chrome",
        }
        with patch("api.views.recorder.start_session", return_value=mock_data):
            client = APIClient()
            response = client.post(
                "/api/recorder/start",
                {"url": "https://example.com"},
                format="json",
            )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["session_id"] == "test-session-123"


@pytest.mark.django_db
class TestRecorderLiveViewView:
    """Tests for GET /api/recorder/<session_id>/live-view"""

    def test_live_view_missing_browserbase_session_id_returns_400(self):
        """Missing browserbase_session_id query param returns 400."""
        client = APIClient()
        response = client.get("/api/recorder/session-123/live-view")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "browserbase_session_id" in response.data["error"]

    def test_live_view_with_param_success(self):
        """With browserbase_session_id, returns live_view_url (mocked)."""
        with patch("api.views.recorder.get_live_view_url", return_value="https://live.example.com"):
            client = APIClient()
            response = client.get(
                "/api/recorder/session-123/live-view",
                {"browserbase_session_id": "bb-session-456"},
            )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["live_view_url"] == "https://live.example.com"


@pytest.mark.django_db
class TestRecorderStartRecordingView:
    """Tests for POST /api/recorder/<session_id>/start-recording"""

    def test_start_recording_missing_browserbase_session_id_returns_400(self):
        """Missing browserbase_session_id in body returns 400."""
        client = APIClient()
        response = client.post(
            "/api/recorder/session-123/start-recording",
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "browserbase_session_id" in response.data["error"]

    def test_start_recording_with_param_success(self):
        """With browserbase_session_id, returns 200 (mocked start_recording)."""
        with patch("api.views.recorder.start_recording"):
            client = APIClient()
            response = client.post(
                "/api/recorder/session-123/start-recording",
                {"browserbase_session_id": "bb-session-456"},
                format="json",
            )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True


@pytest.mark.django_db
class TestRecorderToggleRecordingView:
    """Tests for POST /api/recorder/<session_id>/toggle-recording"""

    def test_toggle_recording_session_not_found_returns_404(self):
        """Unknown session returns 404."""
        client = APIClient()
        response = client.post(
            "/api/recorder/nonexistent-session/toggle-recording",
            {"enabled": True},
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "error" in response.data


@pytest.mark.django_db
class TestRecorderGetRecordedActionsView:
    """Tests for GET /api/recorder/<session_id>/recorded-actions"""

    def test_recorded_actions_session_not_in_state_returns_session_closed(self):
        """Session not in state returns success with session_closed=True."""
        client = APIClient()
        response = client.get("/api/recorder/nonexistent-session/recorded-actions")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["session_closed"] is True
        assert response.data["actions"] == []


@pytest.mark.django_db
class TestRecorderEndView:
    """Tests for POST /api/recorder/<session_id>/end"""

    def test_end_session_success(self):
        """End session returns 200 (mocked end_session)."""
        with patch("api.views.recorder.end_session"):
            client = APIClient()
            response = client.post(
                "/api/recorder/session-123/end",
                {"browserbase_session_id": "bb-session-456"},
                format="json",
            )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True


@pytest.mark.django_db
class TestRecorderSaveTestView:
    """Tests for POST /api/recorder/save-test"""

    def test_save_test_unauthenticated_returns_403(self):
        """Unauthenticated request returns 403 (DRF IsAuthenticated rejects before view)."""
        client = APIClient()
        response = client.post(
            "/api/recorder/save-test",
            {
                "name": "Test",
                "expected_behavior": "Should work",
                "url": "https://example.com",
                "steps": [{"type": "goto", "url": "https://example.com"}],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "detail" in response.data

    def test_save_test_missing_name_returns_400(self):
        """Missing name returns 400."""
        user = User.objects.create_user(username="testuser", email="test@example.com", password="pass")
        with patch("api.views.recorder.summarize_steps", return_value="summary"):
            client = APIClient()
            client.force_authenticate(user=user)
            response = client.post(
                "/api/recorder/save-test",
                {
                    "expected_behavior": "Should work",
                    "url": "https://example.com",
                    "steps": [{"type": "goto", "url": "https://example.com"}],
                },
                format="json",
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "name" in response.data["error"]

    def test_save_test_success(self):
        """Authenticated user with valid data creates test."""
        user = User.objects.create_user(username="testuser", email="test@example.com", password="pass")
        with patch("api.views.recorder.summarize_steps", return_value="summary"):
            client = APIClient()
            client.force_authenticate(user=user)
            response = client.post(
                "/api/recorder/save-test",
                {
                    "name": "My Test",
                    "expected_behavior": "Should work",
                    "url": "https://example.com",
                    "steps": [{"type": "goto", "url": "https://example.com"}],
                },
                format="json",
            )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["test_name"] == "My Test"
        assert response.data["url"] == "https://example.com"
        assert "id" in response.data
