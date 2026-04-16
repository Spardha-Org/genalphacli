from rest_framework import viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.views import APIView


class UserViewSet(viewsets.ModelViewSet):
    """CRUD operations for users."""

    def list(self, request):
        """List all users."""
        return Response([])

    def create(self, request):
        """Create a user."""
        return Response({})

    def retrieve(self, request, pk=None):
        """Get a single user."""
        return Response({})

    def update(self, request, pk=None):
        """Update a user."""
        return Response({})

    def partial_update(self, request, pk=None):
        """Partially update a user."""
        return Response({})

    def destroy(self, request, pk=None):
        """Delete a user."""
        return Response({})

    @action(detail=True, methods=["post"])
    def set_password(self, request, pk=None):
        """Set user password."""
        return Response({})

    @action(detail=False, methods=["get"])
    def recent(self, request):
        """Get recent users."""
        return Response([])


class PostViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only post endpoints."""

    def list(self, request):
        return Response([])

    def retrieve(self, request, pk=None):
        return Response({})


class StatsView(APIView):
    """API stats endpoint."""

    def get(self, request):
        """Get API statistics."""
        return Response({})

    def post(self, request):
        """Reset API statistics."""
        return Response({})
