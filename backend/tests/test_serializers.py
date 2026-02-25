"""
Tests for core serializers (UserSerializer, TestSerializer,
TestExecutionSerializer, TestResultSerializer).
"""

import pytest

from core.models import Test, TestExecution, TestResult, User
from core.serializers import (
    TestExecutionSerializer,
    TestResultSerializer,
    TestSerializer,
    UserSerializer,
)


@pytest.mark.django_db
class TestUserSerializer:
    """Tests for UserSerializer."""

    def test_serializes_expected_fields(self, user):
        """Serializer includes all expected fields."""
        data = UserSerializer(user).data
        assert data["id"] == str(user.id)
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert "created_at" in data
        assert "token_limit" in data
        assert "tokens_used" in data
        assert "concurrent_browser_limit" in data
        assert "browser_hours_limit" in data

    def test_password_not_exposed(self, user):
        """Password field is not in serialized output."""
        data = UserSerializer(user).data
        assert "password" not in data


@pytest.mark.django_db
class TestTestSerializer:
    """Tests for TestSerializer."""

    def test_serializes_expected_fields(self, test_obj):
        """Serializer includes all expected fields."""
        data = TestSerializer(test_obj).data
        assert data["id"] == str(test_obj.id)
        assert data["test_name"] == "Sample Test"
        assert data["url"] == "https://example.com"
        assert "steps" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_read_only_fields(self):
        """id, created_at, and updated_at are read-only."""
        serializer = TestSerializer()
        ro = serializer.Meta.read_only_fields
        assert "id" in ro
        assert "created_at" in ro
        assert "updated_at" in ro


@pytest.mark.django_db
class TestTestExecutionSerializer:
    """Tests for TestExecutionSerializer."""

    def test_serializes_expected_fields(self, execution):
        """Serializer includes all expected fields."""
        data = TestExecutionSerializer(execution).data
        assert data["id"] == str(execution.id)
        assert data["test_name"] == execution.test_name
        assert data["status"] == "pending"
        assert data["progress"] == 0
        assert "url" in data
        assert "steps" in data

    def test_read_only_fields(self):
        """Status, progress, and timing fields are read-only."""
        serializer = TestExecutionSerializer()
        ro = serializer.Meta.read_only_fields
        for field in ["id", "status", "progress", "message", "total_runtime_sec"]:
            assert field in ro


@pytest.mark.django_db
class TestTestResultSerializer:
    """Tests for TestResultSerializer."""

    def test_serializes_expected_fields(self, test_result):
        """Serializer includes all expected fields."""
        data = TestResultSerializer(test_result).data
        assert data["id"] == str(test_result.id)
        assert data["success"] is True
        assert data["total_steps"] == 1
        assert data["passed_steps"] == 1
        assert "executed_steps" in data
        assert "url" in data

    def test_read_only_fields(self):
        """id, created_at, updated_at are read-only."""
        serializer = TestResultSerializer()
        ro = serializer.Meta.read_only_fields
        assert "id" in ro
        assert "created_at" in ro
        assert "updated_at" in ro
