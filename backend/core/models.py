"""
Database models for ReplayQA
"""

import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Custom user manager"""

    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(username, email, password, **extra_fields)


class User(AbstractBaseUser):
    """
    Custom User model
    Stores user accounts and authentication data
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    company = models.CharField(max_length=255, null=True, blank=True)
    token_limit = models.IntegerField(default=0)
    tokens_used = models.BigIntegerField(default=0)
    tokens_used_this_month = models.BigIntegerField(default=0)
    last_token_reset = models.DateTimeField(null=True, blank=True)
    concurrent_browser_limit = models.IntegerField(default=1)
    browser_hours_limit = models.IntegerField(default=0)  # Per month
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return self.username


class Test(models.Model):
    """
    Saved Test model
    Stores reusable test definitions
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="saved_tests")
    test_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    url = models.URLField(max_length=2000)
    steps = models.JSONField()  # Instructions/steps as JSON
    expected_behavior = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "test"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.test_name} ({self.user.username})"


class TestExecution(models.Model):
    """
    Test Execution model
    Stores test execution runs and their status
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Link to saved Test; Django creates test_id column automatically for this FK
    test = models.ForeignKey(
        Test,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="executions",
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="test_executions"
    )
    test_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    url = models.URLField(max_length=2000)
    steps = models.JSONField()  # Instructions/steps as JSON
    expected_behavior = models.TextField(blank=True)
    browserbase_session_id = models.CharField(max_length=255, null=True, blank=True)
    live_view_url = models.URLField(max_length=1024, null=True, blank=True)
    device = models.CharField(max_length=20, default="desktop")
    browser = models.CharField(max_length=20, default="chrome")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    progress = models.IntegerField(default=0)  # 0-100
    message = models.TextField(null=True, blank=True)
    total_runtime_sec = models.FloatField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "test_execution"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.test_name} - {self.status}"


class TestResult(models.Model):
    """
    Test Result model
    Stores detailed results of completed test executions
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    test_execution = models.OneToOneField(
        TestExecution, on_delete=models.CASCADE, related_name="result"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="test_results"
    )
    test_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    url = models.URLField(max_length=2000)
    steps = models.JSONField()  # Instructions/steps as JSON
    expected_behavior = models.TextField(blank=True)
    success = models.BooleanField(default=False)
    total_steps = models.IntegerField(default=0)
    passed_steps = models.IntegerField(default=0)
    executed_steps = models.JSONField(default=list)  # Array of step objects
    viewport_width = models.IntegerField(null=True, blank=True)
    viewport_height = models.IntegerField(null=True, blank=True)
    cookies_enabled = models.BooleanField(default=True)
    runtime_sec = models.FloatField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    total_tokens = models.IntegerField(default=0)
    agent_output = models.TextField(null=True, blank=True)
    explanation = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "test_result"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.test_name} - {'Passed' if self.success else 'Failed'}"
