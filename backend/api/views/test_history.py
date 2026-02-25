"""
Test History Views
Presentation/API Layer - Endpoints for viewing and managing test execution history
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import TestExecution, TestResult


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_tests(request):
    """
    GET /tests
    List last 50 test executions for the user
    """
    executions = TestExecution.objects.filter(user=request.user).order_by(
        "-created_at"
    )[:50]
    data = [
        {
            "id": str(e.id),
            "test_id": str(e.test_id) if e.test_id else None,
            "test_name": e.test_name,
            "description": e.description,
            "url": e.url,
            "steps": e.steps,
            "expected_behavior": e.expected_behavior,
            "status": e.status,
            "progress": e.progress,
            "message": e.message,
            "total_runtime_sec": e.total_runtime_sec,
            "started_at": e.started_at.isoformat() if e.started_at else None,
            "completed_at": e.completed_at.isoformat() if e.completed_at else None,
            "error_message": e.error_message,
            "is_scheduled": getattr(e, "is_scheduled", False),
            "created_at": e.created_at.isoformat(),
            "updated_at": e.updated_at.isoformat(),
        }
        for e in executions
    ]
    return Response({"results": data})


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_test_result(request, test_result_id):
    """
    DELETE /<test_result_id>
    Delete a test execution result record
    """
    try:
        result = TestResult.objects.get(id=test_result_id, user=request.user)
    except TestResult.DoesNotExist:
        # Also try to find by TestExecution ID
        try:
            execution = TestExecution.objects.get(id=test_result_id, user=request.user)
            # Delete associated result if it exists
            if hasattr(execution, "result"):
                execution.result.delete()
            execution.delete()
            return Response({"message": "Test deleted successfully"})
        except TestExecution.DoesNotExist:
            return Response(
                {"error": "Test not found"}, status=status.HTTP_404_NOT_FOUND
            )

    # Delete the execution too
    if result.test_execution:
        result.test_execution.delete()
    else:
        result.delete()
    return Response({"message": "Test deleted successfully"})
