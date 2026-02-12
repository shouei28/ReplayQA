"""
Tests for database connection
"""

import pytest
from django.db import connection
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestDatabaseConnection:
    """Tests for database connectivity"""

    def test_database_connection(self):
        """Test that database connection works"""
        # Try to execute a simple query
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1

    def test_database_can_create_user(self):
        """Test that we can create and retrieve a user from the database"""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        assert user.id is not None
        assert user.username == "testuser"

        # Verify we can retrieve it
        retrieved_user = User.objects.get(username="testuser")
        assert retrieved_user.id == user.id
        assert retrieved_user.email == "test@example.com"
