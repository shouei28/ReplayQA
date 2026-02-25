"""
Celery tasks for test execution.

Wraps the synchronous execute_test() pipeline so it can be dispatched
asynchronously from the API view, allowing the frontend to poll progress
and display the Browserbase live view while a test is running.
"""

from celery import shared_task

from services.runner.runner_service import execute_test


@shared_task(bind=True, name="services.runner.run_test_execution")
def run_test_execution_task(self, test_execution_id: str):
    """Execute a test in a Celery worker process."""
    return execute_test(test_execution_id)
