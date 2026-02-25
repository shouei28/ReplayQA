"""
Tests for user registration view.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from core.models import User


@pytest.mark.django_db
class TestRegister:
    """Tests for POST /api/auth/register"""

    def test_missing_all_fields_returns_400(self):
        """Missing all required fields returns 400 with errors."""
        client = APIClient()
        response = client.post("/api/auth/register", {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "username" in response.data["errors"]
        assert "email" in response.data["errors"]
        assert "password" in response.data["errors"]

    def test_short_password_returns_400(self):
        """Password shorter than 6 characters returns 400."""
        client = APIClient()
        response = client.post(
            "/api/auth/register",
            {"username": "newuser", "email": "new@example.com", "password": "abc"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.data["errors"]

    def test_duplicate_username_returns_400(self, user):
        """Duplicate username returns 400."""
        client = APIClient()
        response = client.post(
            "/api/auth/register",
            {
                "username": "testuser",  # same as fixture
                "email": "unique@example.com",
                "password": "validpass123",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "username" in response.data["errors"]

    def test_duplicate_email_returns_400(self, user):
        """Duplicate email returns 400."""
        client = APIClient()
        response = client.post(
            "/api/auth/register",
            {
                "username": "uniqueuser",
                "email": "test@example.com",  # same as fixture
                "password": "validpass123",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data["errors"]

    def test_valid_registration_returns_201(self):
        """Valid registration creates user and returns JWT tokens."""
        client = APIClient()
        response = client.post(
            "/api/auth/register",
            {
                "username": "newuser",
                "email": "new@example.com",
                "password": "validpass123",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert "access" in response.data
        assert "refresh" in response.data
        assert response.data["user"]["username"] == "newuser"
        assert response.data["user"]["email"] == "new@example.com"
        assert "id" in response.data["user"]
        # Verify user was actually created in DB
        assert User.objects.filter(username="newuser").exists()
