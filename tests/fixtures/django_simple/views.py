from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def root(request):
    """Root endpoint."""
    return Response({"message": "hello"})


@api_view(["GET"])
def list_users(request, limit: int = 10, offset: int = 0):
    """List all users."""
    return Response([])


@api_view(["GET"])
def get_user(request, user_id: int):
    """Get a user by ID."""
    return Response({})


@api_view(["POST"])
def create_user(request, name: str, email: str, age: int = 25):
    """Create a new user."""
    return Response({})


@api_view(["DELETE"])
def delete_user(request, user_id: int):
    return Response({})
