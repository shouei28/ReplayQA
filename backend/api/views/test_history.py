"""
Test History Views
Presentation/API Layer - Endpoints for viewing and managing test execution history
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_tests(request):
    """
    GET /tests
    List last 50 test results for the user
    
    Returns paginated list of TestResult records ordered by most recent.
    Each result includes basic info (name, status, success, timestamps).
    
    Returns:
    - 200: Array of TestResult objects (max 50)
    - Empty list if no tests found
    """
    # TODO: Implement test list retrieval
    # 1. Query TestResult filtered by user
    # 2. Order by created_at descending
    # 3. Limit to 50 results
    # 4. Return serialized list
    return Response([])


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_test_result(request, test_result_id):
    """
    DELETE /<test_result_id>
    Delete a test execution result record
    
    Removes the TestResult and associated TestExecution from the database.
    Also cleans up associated screenshots from blob storage.
    
    Path Params:
    - test_result_id: UUID of the test result to delete
    
    Returns:
    - 200: Success message
    - 404: Test not found or belongs to another user
    """
    # TODO: Implement test result deletion
    # 1. Get TestResult by ID
    # 2. Verify user ownership
    # 3. Delete associated screenshots from blob storage
    # 4. Delete TestResult and TestExecution
    # 5. Return success message
    return Response({
        'message': 'Test deleted successfully'
    })
