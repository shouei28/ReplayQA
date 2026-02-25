"""
Serializers for core models
"""

from rest_framework import serializers

from .models import Test, TestExecution, TestResult, User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "company",
            "token_limit",
            "tokens_used",
            "tokens_used_this_month",
            "concurrent_browser_limit",
            "browser_hours_limit",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class TestSerializer(serializers.ModelSerializer):
    """Serializer for Test (saved test) model"""

    class Meta:
        model = Test
        fields = [
            "id",
            "test_name",
            "description",
            "url",
            "steps",
            "expected_behavior",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TestExecutionSerializer(serializers.ModelSerializer):
    """Serializer for TestExecution model"""

    class Meta:
        model = TestExecution
        fields = [
            "id",
            "test_id",
            "test_name",
            "description",
            "url",
            "steps",
            "expected_behavior",
            "status",
            "progress",
            "message",
            "total_runtime_sec",
            "browserbase_session_id",
            "started_at",
            "completed_at",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "progress",
            "message",
            "total_runtime_sec",
            "browserbase_session_id",
            "started_at",
            "completed_at",
            "error_message",
            "created_at",
            "updated_at",
        ]


class TestResultSerializer(serializers.ModelSerializer):
    """Serializer for TestResult model"""

    class Meta:
        model = TestResult
        fields = [
            "id",
            "test_name",
            "description",
            "url",
            "steps",
            "expected_behavior",
            "success",
            "total_steps",
            "passed_steps",
            "executed_steps",
            "viewport_width",
            "viewport_height",
            "cookies_enabled",
            "runtime_sec",
            "started_at",
            "total_tokens",
            "agent_output",
            "explanation",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
