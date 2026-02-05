"""
API Views Package
Presentation/API Layer - Exposes API endpoints, handles authentication, validation, and response formatting
"""
from .pipeline import run_pipeline, get_test_status, get_test_results, get_live_view
from .test_history import list_tests, delete_test_result
from .saved_tests import saved_tests_list_create, saved_test_detail
from .auth import get_auth_me, auth_logout
from .admin import admin_management
from .misc import health_check, get_screenshot

__all__ = [
    'run_pipeline',
    'get_test_status',
    'get_test_results',
    'get_live_view',
    'list_tests',
    'delete_test_result',
    'saved_tests_list_create',
    'saved_test_detail',
    'get_auth_me',
    'auth_logout',
    'admin_management',
    'health_check',
    'get_screenshot',
]
