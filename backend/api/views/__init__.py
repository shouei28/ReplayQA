"""
API Views Package
Presentation/API Layer - Exposes API endpoints, handles authentication, validation, and response formatting
"""

from .admin import admin_management
from .auth import auth_logout, get_auth_me
from .misc import get_screenshot, health_check
from .pipeline import get_live_view, get_test_results, get_test_status, run_pipeline
from .saved_tests import saved_test_detail, saved_tests_list_create
from .test_history import delete_test_result, list_tests

__all__ = [
    "run_pipeline",
    "get_test_status",
    "get_test_results",
    "get_live_view",
    "list_tests",
    "delete_test_result",
    "saved_tests_list_create",
    "saved_test_detail",
    "get_auth_me",
    "auth_logout",
    "admin_management",
    "health_check",
    "get_screenshot",
]
