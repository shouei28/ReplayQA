"""
Pytest configuration and shared fixtures for ReplayQA backend tests.
"""

import pytest
from rest_framework.test import APIClient

from core.models import Test, TestExecution, TestResult, User


@pytest.fixture
def user(db):
    """Create a standard test user."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )


@pytest.fixture
def admin_user(db):
    """Create an admin/staff test user."""
    return User.objects.create_superuser(
        username="adminuser",
        email="admin@example.com",
        password="adminpass123",
    )


@pytest.fixture
def other_user(db):
    """Create a second user for ownership/isolation tests."""
    return User.objects.create_user(
        username="otheruser",
        email="other@example.com",
        password="otherpass123",
    )


@pytest.fixture
def auth_client(user):
    """Return an APIClient authenticated as the default test user."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def admin_client(admin_user):
    """Return an APIClient authenticated as an admin user."""
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def test_obj(user):
    """Create a saved Test instance."""
    return Test.objects.create(
        user=user,
        test_name="Sample Test",
        description="A sample test",
        url="https://example.com",
        steps=[{"type": "goto", "url": "https://example.com"}],
        expected_behavior="Page loads successfully",
    )


@pytest.fixture
def execution(user, test_obj):
    """Create a TestExecution instance linked to test_obj."""
    return TestExecution.objects.create(
        user=user,
        test=test_obj,
        test_name=test_obj.test_name,
        description=test_obj.description,
        url=test_obj.url,
        steps=test_obj.steps,
        expected_behavior=test_obj.expected_behavior,
        status="pending",
    )


@pytest.fixture
def completed_execution(user, test_obj):
    """Create a completed TestExecution instance."""
    return TestExecution.objects.create(
        user=user,
        test=test_obj,
        test_name=test_obj.test_name,
        description=test_obj.description,
        url=test_obj.url,
        steps=test_obj.steps,
        expected_behavior=test_obj.expected_behavior,
        status="completed",
    )


@pytest.fixture
def test_result(user, completed_execution):
    """Create a TestResult linked to the completed execution."""
    return TestResult.objects.create(
        test_execution=completed_execution,
        user=user,
        test_name=completed_execution.test_name,
        description=completed_execution.description,
        url=completed_execution.url,
        steps=completed_execution.steps,
        expected_behavior=completed_execution.expected_behavior,
        success=True,
        total_steps=1,
        passed_steps=1,
        executed_steps=[{"step_number": 1, "status": "passed"}],
    )
