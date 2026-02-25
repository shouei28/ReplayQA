"""
Tests for core models: User, Test, TestExecution, TestResult,
and basic database connectivity.
"""

import pytest
from django.db import connection

from core.models import Test, TestExecution, TestResult, User


@pytest.mark.django_db
class TestDatabaseConnection:
    """Tests for database connectivity."""

    def test_database_connection(self):
        """Test that database connection works."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1

    def test_database_can_create_user(self):
        """Test that we can create and retrieve a user from the database."""
        user = User.objects.create_user(
            username="dbuser", email="db@example.com", password="testpass123"
        )
        assert user.id is not None
        assert user.username == "dbuser"

        retrieved_user = User.objects.get(username="dbuser")
        assert retrieved_user.id == user.id
        assert retrieved_user.email == "db@example.com"


@pytest.mark.django_db
class TestUserModel:
    """Tests for the User model and UserManager."""

    def test_str_returns_username(self, user):
        """__str__ returns the username."""
        assert str(user) == "testuser"

    def test_create_user_without_email_raises(self):
        """create_user without email raises ValueError."""
        with pytest.raises(ValueError, match="Email"):
            User.objects.create_user(
                username="noemail", email="", password="testpass123"
            )

    def test_create_superuser_sets_flags(self):
        """create_superuser sets is_staff and is_superuser to True."""
        admin = User.objects.create_superuser(
            username="superadmin", email="super@example.com", password="adminpass"
        )
        assert admin.is_staff is True
        assert admin.is_superuser is True

    def test_user_default_field_values(self, user):
        """Newly created user has expected default field values."""
        assert user.token_limit == 0
        assert user.tokens_used == 0
        assert user.concurrent_browser_limit == 1
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False


@pytest.mark.django_db
class TestTestModel:
    """Tests for the Test (saved test) model."""

    def test_str_format(self, test_obj):
        """__str__ returns 'test_name (username)' format."""
        assert str(test_obj) == "Sample Test (testuser)"

    def test_create_with_all_fields(self, user):
        """Test can be created with all fields."""
        t = Test.objects.create(
            user=user,
            test_name="Full Test",
            description="Full description",
            url="https://full.example.com",
            steps=[{"type": "click", "selector": "#btn"}],
            expected_behavior="Button clicked",
        )
        assert t.id is not None
        assert t.created_at is not None
        assert t.updated_at is not None

    def test_ordering_is_newest_first(self, user):
        """Default ordering is -created_at (newest first)."""
        t1 = Test.objects.create(
            user=user, test_name="First", url="https://a.com", steps=[]
        )
        t2 = Test.objects.create(
            user=user, test_name="Second", url="https://b.com", steps=[]
        )
        tests = list(Test.objects.filter(user=user))
        assert tests[0].id == t2.id
        assert tests[1].id == t1.id

    def test_cascade_delete_with_user(self, user, test_obj):
        """Deleting user cascades to tests."""
        user.delete()
        assert not Test.objects.filter(id=test_obj.id).exists()


@pytest.mark.django_db
class TestTestExecutionModel:
    """Tests for the TestExecution model."""

    def test_str_format(self, execution):
        """__str__ returns 'test_name - status' format."""
        assert str(execution) == "Sample Test - pending"

    def test_status_choices(self, execution):
        """Status can be updated to any valid choice."""
        for choice in ["pending", "running", "completed", "failed", "cancelled"]:
            execution.status = choice
            execution.save()
            execution.refresh_from_db()
            assert execution.status == choice

    def test_fk_to_test_is_nullable(self, user):
        """TestExecution can exist without a linked Test (test FK is nullable)."""
        exe = TestExecution.objects.create(
            user=user,
            test=None,
            test_name="Standalone",
            url="https://example.com",
            steps=[{"type": "goto"}],
        )
        assert exe.test is None
        assert exe.id is not None


@pytest.mark.django_db
class TestTestResultModel:
    """Tests for the TestResult model."""

    def test_str_passed(self, test_result):
        """__str__ shows 'Passed' when success is True."""
        assert "Passed" in str(test_result)

    def test_str_failed(self, test_result):
        """__str__ shows 'Failed' when success is False."""
        test_result.success = False
        test_result.save()
        assert "Failed" in str(test_result)

    def test_one_to_one_with_execution(self, test_result, completed_execution):
        """TestResult is one-to-one with TestExecution."""
        assert test_result.test_execution == completed_execution
        assert completed_execution.result == test_result

    def test_cascade_delete_from_execution(self, test_result, completed_execution):
        """Deleting execution cascades to result."""
        result_id = test_result.id
        completed_execution.delete()
        assert not TestResult.objects.filter(id=result_id).exists()
