from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Test, TestExecution, TestResult


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'company', 'token_limit', 'tokens_used', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    filter_horizontal = ()  # Custom User has no groups/user_permissions
    fieldsets = BaseUserAdmin.fieldsets + (
        ('ReplayQA Settings', {
            'fields': ('company', 'token_limit', 'tokens_used', 'tokens_used_this_month',
                      'last_token_reset', 'concurrent_browser_limit', 'browser_hours_limit')
        }),
    )


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('test_name', 'user', 'url', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('test_name', 'user__username', 'url')


@admin.register(TestExecution)
class TestExecutionAdmin(admin.ModelAdmin):
    list_display = ('test_name', 'user', 'status', 'progress', 'started_at', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('test_name', 'user__username', 'url')


@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ('test_name', 'user', 'success', 'passed_steps', 'total_steps', 'created_at')
    list_filter = ('success', 'created_at')
    search_fields = ('test_name', 'user__username')
