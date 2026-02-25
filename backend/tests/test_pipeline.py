import sys
import uuid
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from core.models import TestExecution


# Ensure the mock module is available for patching even when
# the real runner_service can't be imported (e.g. missing deps in CI).
if "services.runner.runner_service" not in sys.modules:
    sys.modules["services.runner.runner_service"] = ModuleType(
        "services.runner.runner_service"
    )


@pytest.mark.django_db
class TestRunPipeline:
    """Tests for POST /api/run-pipeline"""

    def test_unauthenticated_returns_401(self):
        """Unauthenticated request returns 401."""
        client = APIClient()
        response = client.post("/api/run-pipeline", {}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_missing_url_returns_400(self, auth_client):
        """Missing url field returns 400."""
        response = auth_client.post(
            "/api/run-pipeline",
            {"description": "Test", "steps": [{"type": "goto"}]},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "url" in response.data

    def test_missing_description_returns_400(self, auth_client):
        """Missing description field returns 400."""
        response = auth_client.post(
            "/api/run-pipeline",
            {"url": "https://example.com", "steps": [{"type": "goto"}]},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "description" in response.data

    def test_missing_steps_returns_400(self, auth_client):
        """Missing steps field returns 400."""
        response = auth_client.post(
            "/api/run-pipeline",
            {"url": "https://example.com", "description": "Test"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "steps" in response.data

    def test_empty_steps_returns_400(self, auth_client):
        """Empty steps array returns 400."""
        response = auth_client.post(
            "/api/run-pipeline",
            {"url": "https://example.com", "description": "Test", "steps": []},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "steps" in response.data

    def test_success_returns_201(self, auth_client):
        """Valid payload creates execution and returns 201."""
        mock_mod = ModuleType("services.runner.runner_service")
        mock_execute = MagicMock(return_value={"status": "completed"})
        mock_mod.execute_test = mock_execute
        with patch.dict(sys.modules, {"services.runner.runner_service": mock_mod}):
            response = auth_client.post(
                "/api/run-pipeline",
                {
                    "url": "https://example.com",
                    "description": "My test desc",
                    "steps": [{"type": "goto", "url": "https://example.com"}],
                },
                format="json",
            )
        assert response.status_code == status.HTTP_201_CREATED
        assert "job_id" in response.data
        assert response.data["status"] == "completed"
        assert TestExecution.objects.count() == 1

    def test_execution_failure_returns_500(self, auth_client):
        """When execute_test raises, returns 500 with error message."""
        mock_mod = ModuleType("services.runner.runner_service")
        mock_execute = MagicMock(side_effect=Exception("Browserbase failed"))
        mock_mod.execute_test = mock_execute
        with patch.dict(sys.modules, {"services.runner.runner_service": mock_mod}):
            response = auth_client.post(
                "/api/run-pipeline",
                {
                    "url": "https://example.com",
                    "description": "Failing test",
                    "steps": [{"type": "goto", "url": "https://example.com"}],
                },
                format="json",
            )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data["status"] == "failed"

    def test_browser_hours_limit_exceeded_returns_403(self, auth_client, user):
        """When user exceeds browser-hours limit, returns 403."""
        user.browser_hours_limit = 1  # 1 hour limit
        user.save()
        # Create a completed execution with 2 hours of runtime
        TestExecution.objects.create(
            user=user,
            test_name="Past test",
            url="https://example.com",
            steps=[{"type": "goto"}],
            status="completed",
            total_runtime_sec=7200,  # 2 hours
        )
        response = auth_client.post(
            "/api/run-pipeline",
            {
                "url": "https://example.com",
                "description": "Over limit",
                "steps": [{"type": "goto", "url": "https://example.com"}],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("services.runner.runner_service.execute_test", create=True)
    def test_linked_test_not_found_returns_400(self, mock_execute, auth_client):
        """Linking to a non-existent test_id returns 400."""
        response = auth_client.post(
            "/api/run-pipeline",
            {
                "url": "https://example.com",
                "description": "Test",
                "steps": [{"type": "goto"}],
                "test_id": str(uuid.uuid4()),
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "test_id" in response.data


@pytest.mark.django_db
class TestGetTestStatus:
    """Tests for GET /api/status/<test_execution_id>"""

    def test_unauthenticated_returns_401(self):
        """Unauthenticated request returns 401."""
        client = APIClient()
        response = client.get(f"/api/status/{uuid.uuid4()}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_not_found_returns_404(self, auth_client):
        """Non-existent execution returns 404."""
        response = auth_client.get(f"/api/status/{uuid.uuid4()}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_success_returns_serialized_execution(self, auth_client, execution):
        """Returns serialized execution data for valid ID."""
        response = auth_client.get(f"/api/status/{execution.id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(execution.id)
        assert response.data["status"] == "pending"
        assert response.data["test_name"] == execution.test_name


@pytest.mark.django_db
class TestGetTestResults:
    """Tests for GET /api/results/<test_execution_id>"""

    def test_not_found_returns_404(self, auth_client):
        """Non-existent execution returns 404."""
        response = auth_client.get(f"/api/results/{uuid.uuid4()}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_still_running_returns_400(self, auth_client, execution):
        """Pending/running execution returns 400."""
        response = auth_client.get(f"/api/results/{execution.id}")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "still running" in response.data["detail"]

    def test_completed_returns_result(
        self, auth_client, completed_execution, test_result
    ):
        """Completed execution returns the test result."""
        response = auth_client.get(f"/api/results/{completed_execution.id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["test_name"] == completed_execution.test_name
        assert response.data["success"] is True


@pytest.mark.django_db
class TestGetLiveView:
    """Tests for GET /api/live-view/<test_execution_id>/"""

    def test_not_found_returns_404(self, auth_client):
        """Non-existent execution returns 404."""
        response = auth_client.get(f"/api/live-view/{uuid.uuid4()}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_not_running_returns_400(self, auth_client, execution):
        """Non-running execution returns 400."""
        response = auth_client.get(f"/api/live-view/{execution.id}/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "not currently running" in response.data["detail"]

    def test_running_without_bb_session_returns_400(self, auth_client, execution):
        """Running execution without browserbase_session_id returns 400."""
        execution.status = "running"
        execution.save()
        response = auth_client.get(f"/api/live-view/{execution.id}/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "not been created" in response.data["detail"]

    @patch(
        "services.recorder.session_service.get_live_view_url",
        return_value="https://live.bb.com",
    )
    def test_running_with_bb_session_returns_url(
        self, mock_live_view, auth_client, execution
    ):
        """Running execution with bb session returns live view URL."""
        execution.status = "running"
        execution.browserbase_session_id = "bb-sess-123"
        execution.save()
        response = auth_client.get(f"/api/live-view/{execution.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["live_view_url"] == "https://live.bb.com"
        assert response.data["session_id"] == "bb-sess-123"
