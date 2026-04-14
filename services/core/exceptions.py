"""Domain exceptions — mapped to HTTP status codes by the global error handler.

Services throw these. Routes never import HTTPException.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base exception for all domain errors."""

    status_code: int = 500
    detail: str = "Internal server error"

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


class NotFoundError(DomainError):
    status_code = 404
    detail = "Resource not found"


class UnauthorizedError(DomainError):
    status_code = 401
    detail = "Not authenticated"


class ForbiddenError(DomainError):
    status_code = 403
    detail = "Permission denied"


class ConflictError(DomainError):
    status_code = 409
    detail = "Resource already exists"


class ValidationError(DomainError):
    status_code = 422
    detail = "Validation error"


class ServiceUnavailableError(DomainError):
    status_code = 503
    detail = "Service temporarily unavailable"
