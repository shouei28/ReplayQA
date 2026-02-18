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


@shared_task(name="core.tasks.run_test_execution", bind=True, max_retries=1)
def run_test_execution(self, test_execution_id):
    """
    Execute a test using Stagehand and evaluate results with Gemini.

    This is the main background task queued by the ``run_pipeline`` API
    endpoint.  It delegates entirely to
    ``services.runner.runner_service.execute_test``.

    Args:
        test_execution_id: UUID (str) of the TestExecution record.

    Returns:
        dict: Execution result with status, test_result_id, etc.
    """
    logger.info("Celery task started for execution %s", test_execution_id)
    try:
        from services.runner.runner_service import execute_test

        result = execute_test(test_execution_id)
        logger.info(
            "Celery task finished for %s — %s", test_execution_id, result.get("status")
        )
        return result
    except Exception as exc:
        logger.error(
            "Celery task failed for %s: %s", test_execution_id, exc, exc_info=True
        )
        # Mark the execution as failed so the frontend sees a terminal state.
        try:
            from core.models import TestExecution
            from django.utils import timezone

            execution = TestExecution.objects.get(id=test_execution_id)
            execution.status = "failed"
            execution.error_message = str(exc)
            execution.message = f"Task error: {exc}"
            execution.completed_at = timezone.now()
            execution.save()
        except Exception:
            pass
        raise
