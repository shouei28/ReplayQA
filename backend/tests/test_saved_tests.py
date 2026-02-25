"""
Tests for saved tests CRUD views.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Test


@pytest.mark.django_db
class TestSavedTestsListCreate:
    """Tests for GET/POST /api/saved-tests"""

    def test_list_unauthenticated_returns_401(self):
        """Unauthenticated request returns 401."""
        client = APIClient()
        response = client.get("/api/saved-tests")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_empty_returns_200(self, auth_client):
        """Returns empty list when user has no saved tests."""
        response = auth_client.get("/api/saved-tests")
        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_list_returns_user_tests_only(self, auth_client, test_obj, other_user):
        """Returns only tests belonging to the authenticated user."""
        # Create a test for other_user — should not appear
        Test.objects.create(
            user=other_user,
            test_name="Other Test",
            url="https://other.com",
            steps=[{"type": "goto"}],
        )
        response = auth_client.get("/api/saved-tests")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["test_name"] == "Sample Test"

    def test_create_missing_test_name_returns_400(self, auth_client):
        """Missing test_name returns 400."""
        response = auth_client.post(
            "/api/saved-tests",
            {"url": "https://example.com", "steps": [{"type": "goto"}]},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "test_name" in response.data["error"]

    def test_create_missing_url_returns_400(self, auth_client):
        """Missing url returns 400."""
        response = auth_client.post(
            "/api/saved-tests",
            {"test_name": "Test", "steps": [{"type": "goto"}]},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "url" in response.data["error"]

    def test_create_missing_steps_returns_400(self, auth_client):
        """Missing steps returns 400."""
        response = auth_client.post(
            "/api/saved-tests",
            {"test_name": "Test", "url": "https://example.com"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "steps" in response.data["error"]

    def test_create_success(self, auth_client, user):
        """Valid payload creates a saved test and returns 201."""
        response = auth_client.post(
            "/api/saved-tests",
            {
                "test_name": "New Test",
                "description": "Desc",
                "url": "https://example.com",
                "steps": [{"type": "click", "selector": "#btn"}],
                "expected_behavior": "Button is clicked",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["test_name"] == "New Test"
        assert response.data["url"] == "https://example.com"
        assert "id" in response.data
        assert Test.objects.filter(user=user, test_name="New Test").exists()


@pytest.mark.django_db
class TestSavedTestDetail:
    """Tests for GET/PUT/DELETE /api/saved-tests/<test_id>"""

    def test_get_returns_test(self, auth_client, test_obj):
        """GET returns the test details."""
        response = auth_client.get(f"/api/saved-tests/{test_obj.id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["test_name"] == "Sample Test"

    def test_get_other_user_test_returns_404(self, auth_client, other_user):
        """Accessing another user's test returns 404."""
        other_test = Test.objects.create(
            user=other_user,
            test_name="Other",
            url="https://other.com",
            steps=[{"type": "goto"}],
        )
        response = auth_client.get(f"/api/saved-tests/{other_test.id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_put_partial_update(self, auth_client, test_obj):
        """PUT with partial data updates only provided fields."""
        response = auth_client.put(
            f"/api/saved-tests/{test_obj.id}",
            {"test_name": "Updated Name"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["test_name"] == "Updated Name"
        # Unchanged fields remain
        assert response.data["url"] == "https://example.com"

    def test_delete_success(self, auth_client, test_obj):
        """DELETE removes the test and returns 200."""
        response = auth_client.delete(f"/api/saved-tests/{test_obj.id}")
        assert response.status_code == status.HTTP_200_OK
        assert not Test.objects.filter(id=test_obj.id).exists()

    def test_delete_nonexistent_returns_404(self, auth_client):
        """DELETE on a non-existent test returns 404."""
        import uuid

        response = auth_client.delete(f"/api/saved-tests/{uuid.uuid4()}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
