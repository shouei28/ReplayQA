"""
User Registration View
"""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    """
    POST /api/auth/register
    Create a new user account and return JWT tokens.

    Body: { "username": str, "email": str, "password": str }
    Returns: { "access": str, "refresh": str, "user": {...} }
    """
    username = request.data.get("username", "").strip()
    email = request.data.get("email", "").strip()
    password = request.data.get("password", "")

    errors = {}
    if not username:
        errors["username"] = "Username is required."
    if not email:
        errors["email"] = "Email is required."
    if not password or len(password) < 6:
        errors["password"] = "Password must be at least 6 characters."

    if User.objects.filter(username=username).exists():
        errors["username"] = "Username already taken."
    if email and User.objects.filter(email=email).exists():
        errors["email"] = "Email already registered."

    if errors:
        return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
    )

    refresh = RefreshToken.for_user(user)

    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
            },
        },
        status=status.HTTP_201_CREATED,
    )
