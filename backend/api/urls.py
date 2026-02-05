"""
URL routing for API endpoints
"""
from django.urls import path
from .views import (
    health_check,
    run_pipeline,
    get_test_status,
    get_test_results,
    list_tests,
    delete_test_result,
    saved_tests_list_create,
    saved_test_detail,
    get_screenshot,
    get_auth_me,
    auth_logout,
    admin_management,
    get_live_view,
)

urlpatterns = [
    # Health check
    path('health', health_check, name='health'),
    
    # Pipeline Execution
    path('run-pipeline', run_pipeline, name='run-pipeline'),
    path('status/<uuid:test_execution_id>', get_test_status, name='test-status'),
    path('results/<uuid:test_execution_id>', get_test_results, name='test-results'),
    
    # Test History
    path('tests', list_tests, name='list-tests'),
    path('<uuid:test_result_id>', delete_test_result, name='delete-test-result'),
    
    # Saved Tests
    path('saved-tests', saved_tests_list_create, name='saved-tests-list-create'),
    path('saved-tests/<uuid:test_id>', saved_test_detail, name='saved-test-detail'),
    
    # Screenshots
    path('screenshot/<uuid:test_result_id>/<int:step_num>', get_screenshot, name='get-screenshot'),
    
    # Authentication
    path('auth/me', get_auth_me, name='auth-me'),
    path('auth/logout', auth_logout, name='auth-logout'),
    
    # Admin
    path('admin', admin_management, name='admin-management'),
    
    # Live View
    path('live-view/<uuid:test_execution_id>/', get_live_view, name='live-view'),
]
