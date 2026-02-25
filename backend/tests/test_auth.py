"""
Tests for authentication views (get_auth_me, auth_logout).
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestGetAuthMe:
    """Tests for GET /api/auth/me"""

    def test_unauthenticated_returns_401(self):
        """Unauthenticated request returns 401."""
        client = APIClient()
        response = client.get("/api/auth/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_returns_user_profile(self, auth_client, user):
        """Authenticated request returns user profile data."""
        response = auth_client.get("/api/auth/me")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(user.id)
        assert response.data["username"] == "testuser"
        assert response.data["email"] == "test@example.com"

    def test_admin_user_has_admin_flag(self, admin_client, admin_user):
        """Admin user profile includes admin_user=True."""
        response = admin_client.get("/api/auth/me")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["admin_user"] is True


@pytest.mark.django_db
class TestAuthLogout:
    """Tests for POST /api/auth/logout"""

    def test_unauthenticated_returns_401(self):
        """Unauthenticated request returns 401."""
        client = APIClient()
        response = client.post("/api/auth/logout")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_logout_returns_200(self, auth_client):
        """Authenticated logout returns 200 with confirmation."""
        response = auth_client.post("/api/auth/logout")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["detail"] == "Logged out"
