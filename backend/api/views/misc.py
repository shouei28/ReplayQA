"""
Miscellaneous Views
Presentation/API Layer - Utility endpoints (health check, screenshots)
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint
    Returns server status and basic system information
    """
    return Response({"status": "healthy", "service": "ReplayQA Backend"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_screenshot(request, test_result_id, step_num):
    """
    GET /screenshot/<test_result_id>/<step_num>
    Serve screenshot for a test/step

    Returns redirect to screenshot URL from blob storage,
    or serves the image directly if stored locally.

    Path Params:
    - test_result_id: UUID of the test result
    - step_num: Step number (integer) for the screenshot

    Returns:
    - 302: Redirect to screenshot URL
    - 404: Screenshot not found or storage not configured
    """
    # TODO: Implement screenshot serving
    # 1. Get TestResult by ID
    # 2. Verify user ownership
    # 3. Look up screenshot URL from executed_steps or blob storage
    # 4. Return redirect to screenshot URL
    return Response({"error": "Screenshot not found"}, status=status.HTTP_404_NOT_FOUND)
