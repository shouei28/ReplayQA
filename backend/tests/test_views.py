"""
Tests for API views
"""

import pytest
from rest_framework.test import APIClient
from rest_framework import status


@pytest.mark.django_db
class TestHealthCheck:
    """Tests for health check endpoint"""

    def test_health_check(self):
        """Test health check endpoint"""
        client = APIClient()
        response = client.get("/api/health")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "healthy"
