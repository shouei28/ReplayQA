"""
Celery tasks for ReplayQA
Background tasks that can be executed asynchronously
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="core.tasks.test_task")
def test_task():
    """
    Mock test task that prints a message
    This is a placeholder task for testing Celery setup
    """
    print("Test: Celery task executed successfully!")
    logger.info("Test: Celery task executed successfully!")
    return "Task completed"


@shared_task(name="core.tasks.mock_pipeline_task")
def mock_pipeline_task(test_execution_id, url, steps):
    """
    Mock pipeline task for test execution
    This is a placeholder that will be replaced with actual test execution logic

    Args:
        test_execution_id: UUID of the test execution
        url: Target URL to test
        steps: List of test steps to execute

    Returns:
        dict: Task result status
    """
    print(f"Test: Mock pipeline task started for execution {test_execution_id}")
    print(f"Test: URL: {url}")
    print(f"Test: Steps: {steps}")
    logger.info(f"Mock pipeline task started for execution {test_execution_id}")

    # TODO: Replace with actual test execution logic
    # This is just a placeholder that simulates work

    return {
        "status": "completed",
        "test_execution_id": str(test_execution_id),
        "message": "Mock task completed successfully",
    }
