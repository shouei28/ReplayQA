"""
Pipeline Execution Views
Presentation/API Layer - Endpoints for test execution pipeline
"""

import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import Test, TestExecution
from core.serializers import TestExecutionSerializer, TestResultSerializer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# POST /run-pipeline
# ---------------------------------------------------------------------------


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def run_pipeline(request):
    """
    POST /run-pipeline
    Start a new test execution (pipeline run)

    Checks minutes limit for authenticated users before starting execution.
    Creates a TestExecution record and queues the test run in the background.

    Request Body:
    - url (required): Target URL to test
    - description (required): Test description
    - steps (required): JSON array of test steps
    - expected_behavior (optional): Expected behavior description
    - test_id (optional): Link execution to a saved test

    Returns:
    - 201: Job created successfully with job_id and status
    - 403: Minutes limit exceeded
    - 400: Validation failed
    """
    data = request.data
    user = request.user

    # --- Validate required fields -----------------------------------------
    url = data.get("url")
    description = data.get("description")
    steps = data.get("steps")

    errors = {}
    if not url:
        errors["url"] = "This field is required."
    if not description:
        errors["description"] = "This field is required."
    if not steps or not isinstance(steps, list) or len(steps) == 0:
        errors["steps"] = "A non-empty array of test steps is required."
    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    # --- Check browser-hours limit ----------------------------------------
    # A limit of 0 means unlimited.
    if user.browser_hours_limit > 0:
        from django.db.models import Sum

        total_used_sec = (
            TestExecution.objects.filter(user=user, status="completed")
            .aggregate(total=Sum("total_runtime_sec"))
            .get("total")
            or 0
        )
        total_used_hours = total_used_sec / 3600
        if total_used_hours >= user.browser_hours_limit:
            return Response(
                {"detail": "Monthly browser-hours limit exceeded."},
                status=status.HTTP_403_FORBIDDEN,
            )

    # --- Optionally link to a saved Test ----------------------------------
    test_id = data.get("test_id")
    linked_test = None
    if test_id:
        try:
            linked_test = Test.objects.get(id=test_id, user=user)
        except Test.DoesNotExist:
            return Response(
                {"test_id": "Saved test not found or does not belong to you."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # --- Create TestExecution record --------------------------------------
    test_name = data.get("test_name") or description[:255]
    execution = TestExecution.objects.create(
        user=user,
        test=linked_test,
        test_name=test_name,
        description=description,
        url=url,
        steps=steps,
        expected_behavior=data.get("expected_behavior", ""),
        status="pending",
    )

    # --- Run synchronously (no Celery) ------------------------------------
    try:
        from services.runner.runner_service import execute_test

        result = execute_test(str(execution.id))
        exec_status = result.get("status", "completed")
        logger.info(
            "Pipeline run %s finished for user %s: %s",
            execution.id,
            user.username,
            exec_status,
        )
        return Response(
            {
                "job_id": str(execution.id),
                "message": "Test execution completed",
                "status": exec_status,
            },
            status=status.HTTP_201_CREATED,
        )
    except Exception as exc:
        logger.exception("Pipeline run %s failed: %s", execution.id, exc)
        return Response(
            {
                "job_id": str(execution.id),
                "message": str(exc),
                "status": "failed",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ---------------------------------------------------------------------------
# GET /status/<test_execution_id>
# ---------------------------------------------------------------------------


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_test_status(request, test_execution_id):
    """
    GET /status/<test_execution_id>
    Poll execution status and progress of executed test

    Returns current status, progress percentage, and any messages
    from the TestExecution record.

    Path Params:
    - test_execution_id: UUID of the test execution

    Returns:
    - 200: TestExecution data (status, progress, message, etc.)
    - 404: Test execution not found or belongs to another user
    """
    try:
        execution = TestExecution.objects.get(id=test_execution_id, user=request.user)
    except TestExecution.DoesNotExist:
        return Response(
            {"detail": "Test execution not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = TestExecutionSerializer(execution)
    return Response(serializer.data)


# ---------------------------------------------------------------------------
# GET /results/<test_execution_id>
# ---------------------------------------------------------------------------


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_test_results(request, test_execution_id):
    """
    GET /results/<test_execution_id>
    Retrieve full test results and step details

    Returns complete TestResult data including executed steps,
    screenshots references, pass/fail status, and explanations.

    Path Params:
    - test_execution_id: UUID of the test execution

    Returns:
    - 200: Complete TestResult data
    - 400: Test pending or not started
    - 404: Test not found
    - 500: Completed but results missing or invalid
    """
    try:
        execution = TestExecution.objects.get(id=test_execution_id, user=request.user)
    except TestExecution.DoesNotExist:
        return Response(
            {"detail": "Test execution not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if execution.status in ("pending", "running"):
        return Response(
            {
                "detail": "Test is still running.",
                "status": execution.status,
                "progress": execution.progress,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Grab the one-to-one TestResult
    try:
        result = execution.result  # OneToOneField reverse accessor
    except Exception:
        return Response(
            {"detail": "Test completed but result record is missing."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    serializer = TestResultSerializer(result)
    return Response(serializer.data)


# ---------------------------------------------------------------------------
# GET /live-view/<test_execution_id>/
# ---------------------------------------------------------------------------


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_live_view(request, test_execution_id):
    """
    GET /live-view/<test_execution_id>/
    Retrieve Browserbase live view URL for a running test

    Returns the live view URL that allows observing the browser
    session in real-time during test execution.

    Path Params:
    - test_execution_id: UUID of the test execution

    Returns:
    - 200: Live view URL, session_id, device, browser info
    - 400: Test not running
    - 404: Test execution not found
    - 500: Browserbase or server error
    """
    try:
        execution = TestExecution.objects.get(id=test_execution_id, user=request.user)
    except TestExecution.DoesNotExist:
        return Response(
            {"detail": "Test execution not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if execution.status != "running":
        return Response(
            {"detail": "Test is not currently running.", "status": execution.status},
            status=status.HTTP_400_BAD_REQUEST,
        )

    bb_session_id = execution.browserbase_session_id
    if not bb_session_id:
        return Response(
            {"detail": "Browser session has not been created yet."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Fetch live-view URL from Browserbase
    try:
        from services.recorder.session_service import get_live_view_url

        live_url = get_live_view_url(bb_session_id)
    except Exception as exc:
        logger.error("Failed to get live view URL: %s", exc)
        return Response(
            {"detail": "Could not retrieve live view URL."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(
        {
            "live_view_url": live_url,
            "session_id": bb_session_id,
            "device": execution.device,
            "browser": execution.browser,
        }
    )
