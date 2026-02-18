"""
Saved Tests Views
Presentation/API Layer - Endpoints for managing reusable test definitions
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import Test


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def saved_tests_list_create(request):
    """
    GET /saved-tests - Get all saved tests for the current user
    POST /saved-tests - Save a new reusable test definition
    """
    if request.method == "GET":
        tests = Test.objects.filter(user=request.user).order_by("-created_at")
        data = [
            {
                "id": str(t.id),
                "test_name": t.test_name,
                "description": t.description,
                "url": t.url,
                "steps": t.steps,
                "expected_behavior": t.expected_behavior,
                "created_at": t.created_at.isoformat(),
                "updated_at": t.updated_at.isoformat(),
            }
            for t in tests
        ]
        return Response(data)

    # POST
    body = request.data
    test_name = body.get("test_name")
    url = body.get("url")
    steps = body.get("steps")

    if not test_name:
        return Response(
            {"error": "test_name is required"}, status=status.HTTP_400_BAD_REQUEST
        )
    if not url:
        return Response(
            {"error": "url is required"}, status=status.HTTP_400_BAD_REQUEST
        )
    if not steps:
        return Response(
            {"error": "steps is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    test = Test.objects.create(
        user=request.user,
        test_name=test_name,
        description=body.get("description", ""),
        url=url,
        steps=steps,
        expected_behavior=body.get("expected_behavior", ""),
    )
    return Response(
        {
            "id": str(test.id),
            "test_name": test.test_name,
            "description": test.description,
            "url": test.url,
            "steps": test.steps,
            "expected_behavior": test.expected_behavior,
            "created_at": test.created_at.isoformat(),
            "updated_at": test.updated_at.isoformat(),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def saved_test_detail(request, test_id):
    """
    GET /saved-tests/<test_id> - Retrieve one saved test definition
    PUT /saved-tests/<test_id> - Update a saved test definition
    DELETE /saved-tests/<test_id> - Delete a saved test definition
    """
    try:
        test = Test.objects.get(id=test_id, user=request.user)
    except Test.DoesNotExist:
        return Response(
            {"error": "Test not found"}, status=status.HTTP_404_NOT_FOUND
        )

    if request.method == "GET":
        return Response(
            {
                "id": str(test.id),
                "test_name": test.test_name,
                "description": test.description,
                "url": test.url,
                "steps": test.steps,
                "expected_behavior": test.expected_behavior,
                "created_at": test.created_at.isoformat(),
                "updated_at": test.updated_at.isoformat(),
            }
        )

    elif request.method == "PUT":
        body = request.data
        if "test_name" in body:
            test.test_name = body["test_name"]
        if "description" in body:
            test.description = body["description"]
        if "url" in body:
            test.url = body["url"]
        if "steps" in body:
            test.steps = body["steps"]
        if "expected_behavior" in body:
            test.expected_behavior = body["expected_behavior"]
        test.save()
        return Response(
            {
                "id": str(test.id),
                "test_name": test.test_name,
                "description": test.description,
                "url": test.url,
                "steps": test.steps,
                "expected_behavior": test.expected_behavior,
                "created_at": test.created_at.isoformat(),
                "updated_at": test.updated_at.isoformat(),
            }
        )

    else:  # DELETE
        test.delete()
        return Response({"message": "Test deleted successfully"})
