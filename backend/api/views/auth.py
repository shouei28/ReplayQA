"""
Authentication Views
Presentation/API Layer - Endpoints for user authentication and profile management
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_auth_me(request):
    """
    GET /auth/me
    Return current authenticated user profile
    
    Returns user information including id, username, email,
    and admin status.
    
    Returns:
    - 200: User profile data (id, username, email, workspace_user_id, admin_user)
    - 401: Not authenticated
    """
    # TODO: Implement user profile retrieval
    # 1. Get current user from request
    # 2. Return serialized User object
    return Response({
        'id': str(request.user.id) if request.user.is_authenticated else None,
        'username': request.user.username if request.user.is_authenticated else None,
        'email': request.user.email if request.user.is_authenticated else None,
        'admin_user': request.user.is_staff if request.user.is_authenticated else False
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def auth_logout(request):
    """
    POST /auth/logout
    Clear user session
    
    Invalidates the current user's session and JWT token.
    
    Returns:
    - 200: Logout confirmation message
    """
    # TODO: Implement logout logic
    # 1. Invalidate JWT token (if using token blacklist)
    # 2. Clear session
    # 3. Return success message
    return Response({
        'detail': 'Logged out'
    })
