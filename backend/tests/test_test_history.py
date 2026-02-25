"""
Tests for test history views (list_tests, delete_test_result).
"""

import uuid

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from core.models import TestExecution, TestResult


@pytest.mark.django_db
class TestListTests:
    """Tests for GET /api/tests"""

    def test_unauthenticated_returns_401(self):
        """Unauthenticated request returns 401."""
        client = APIClient()
        response = client.get("/api/tests")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_user_executions(self, auth_client, execution):
        """Returns executions belonging to the authenticated user."""
        response = auth_client.get("/api/tests")
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["test_name"] == execution.test_name

    def test_does_not_return_other_user_executions(
        self, auth_client, other_user, execution
    ):
        """Does not return executions belonging to another user."""
        TestExecution.objects.create(
            user=other_user,
            test_name="Other Exec",
            url="https://other.com",
            steps=[{"type": "goto"}],
            status="completed",
        )
        response = auth_client.get("/api/tests")
        assert response.status_code == status.HTTP_200_OK
        # Only the fixture execution should appear
        assert len(response.data["results"]) == 1

    def test_returns_empty_when_no_executions(self, auth_client):
        """Returns empty list when user has no executions."""
        response = auth_client.get("/api/tests")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == []


@pytest.mark.django_db
class TestDeleteTestResult:
    """Tests for DELETE /api/<test_result_id>"""

    def test_delete_by_execution_id(self, auth_client, execution):
        """Delete by TestExecution ID removes the execution."""
        response = auth_client.delete(f"/api/{execution.id}")
        assert response.status_code == status.HTTP_200_OK
        assert not TestExecution.objects.filter(id=execution.id).exists()

    def test_delete_by_result_id(self, auth_client, test_result, completed_execution):
        """Delete by TestResult ID removes both result and execution."""
        response = auth_client.delete(f"/api/{test_result.id}")
        assert response.status_code == status.HTTP_200_OK
        assert not TestResult.objects.filter(id=test_result.id).exists()
        assert not TestExecution.objects.filter(id=completed_execution.id).exists()

    def test_delete_nonexistent_returns_404(self, auth_client):
        """Delete with non-existent ID returns 404."""
        response = auth_client.delete(f"/api/{uuid.uuid4()}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_other_user_execution_returns_404(self, auth_client, other_user):
        """Cannot delete another user's execution."""
        other_exec = TestExecution.objects.create(
            user=other_user,
            test_name="Other",
            url="https://other.com",
            steps=[{"type": "goto"}],
            status="completed",
        )
        response = auth_client.delete(f"/api/{other_exec.id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert TestExecution.objects.filter(id=other_exec.id).exists()
