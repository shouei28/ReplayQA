"""
Celery tasks for ReplayQA
Background tasks that can be executed asynchronously
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


SCHEDULED_TASK_NAME = "core.tasks.run_scheduled_test"


@shared_task(name=SCHEDULED_TASK_NAME)
def run_scheduled_test(test_id: str, user_id: str):
    """
    Run a saved test as a scheduled execution. Called by Celery Beat.

    Creates a TestExecution linked to the Test, sets is_scheduled=True,
    then enqueues run_test_execution so the pipeline runs like a manual run.

    Args:
        test_id: UUID (str) of the saved Test.
        user_id: UUID (str) of the User who owns the test and schedule.
    """
    from django.contrib.auth import get_user_model
    from core.models import Test, TestExecution

    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.error("run_scheduled_test: user %s not found", user_id)
        return {"status": "error", "detail": "User not found"}

    try:
        test = Test.objects.get(id=test_id, user=user)
    except Test.DoesNotExist:
        logger.error("run_scheduled_test: test %s not found for user %s", test_id, user_id)
        return {"status": "error", "detail": "Test not found"}

    # Optional: check browser-hours limit (same as run_pipeline)
    if user.browser_hours_limit > 0:
        from django.db.models import Sum

        total_used_sec = (
            TestExecution.objects.filter(user=user, status="completed")
            .aggregate(total=Sum("total_runtime_sec"))
            .get("total")
            or 0
        )
        if (total_used_sec / 3600) >= user.browser_hours_limit:
            logger.warning("run_scheduled_test: user %s over browser-hours limit", user_id)
            return {"status": "skipped", "detail": "Browser hours limit exceeded"}

    execution = TestExecution.objects.create(
        user=user,
        test=test,
        test_name=test.test_name,
        description=test.description or "",
        url=test.url,
        steps=test.steps,
        expected_behavior=test.expected_behavior or "",
        status="pending",
        is_scheduled=True,
    )

    run_test_execution.delay(str(execution.id))
    logger.info("run_scheduled_test: queued execution %s for test %s", execution.id, test_id)
    return {"status": "queued", "test_execution_id": str(execution.id)}


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
            from django.utils import timezone

            from core.models import TestExecution

            execution = TestExecution.objects.get(id=test_execution_id)
            execution.status = "failed"
            execution.error_message = str(exc)
            execution.message = f"Task error: {exc}"
            execution.completed_at = timezone.now()
            execution.save()
        except Exception:
            pass
        raise
