"""Handler registry for third-party app providers."""

from __future__ import annotations

from typing import Union

from services.tps.handlers.base import AppHandler, CredentialHandler, OAuthHandler
from services.tps.handlers.github import GithubHandler
from services.tps.handlers.pypi import PyPIHandler

# Registry of available handlers — keyed by app_name
HANDLER_REGISTRY: dict[str, type] = {
    "github": GithubHandler,
    "pypi": PyPIHandler,
}


def get_handler(app_name: str) -> Union[OAuthHandler, CredentialHandler]:
    """Get a handler instance for the given app."""
    handler_cls = HANDLER_REGISTRY.get(app_name)
    if not handler_cls:
        raise ValueError(f"No handler for app: {app_name}")
    return handler_cls()


def get_oauth_handler(app_name: str) -> OAuthHandler:
    """Get an OAuth handler, raising if the handler doesn't support OAuth."""
    handler = get_handler(app_name)
    if not isinstance(handler, OAuthHandler):
        raise ValueError(f"App '{app_name}' does not support OAuth flow")
    return handler


def get_credential_handler(app_name: str) -> CredentialHandler:
    """Get a credential handler, raising if the handler doesn't support credentials."""
    handler = get_handler(app_name)
    if not isinstance(handler, CredentialHandler):
        raise ValueError(f"App '{app_name}' does not support credential flow")
    return handler
