"""Handler registry for third-party app providers."""

from services.tps.handlers.github import GithubHandler

# Registry of available handlers
HANDLER_REGISTRY: dict[str, type] = {
    "github": GithubHandler,
}


def get_handler(app_name: str):
    """Get a handler instance for the given app."""
    handler_cls = HANDLER_REGISTRY.get(app_name)
    if not handler_cls:
        raise ValueError(f"No handler for app: {app_name}")
    return handler_cls()
