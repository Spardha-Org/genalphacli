"""CLI code generators — produce installable tools from CommandGraph."""

from __future__ import annotations

from importlib.resources import files

from jinja2.sandbox import SandboxedEnvironment


def get_jinja_env() -> SandboxedEnvironment:
    """Create a sandboxed Jinja2 environment for template rendering.

    Uses SandboxedEnvironment to prevent template injection from
    malicious graph.json field values. Configured for Python code generation.
    """
    templates_path = str(files("genalphacli.generators") / "templates")

    return SandboxedEnvironment(
        loader=_make_loader(templates_path),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


def _make_loader(templates_path: str):  # noqa: ANN202
    """Create a filesystem loader for templates."""
    from jinja2 import FileSystemLoader

    return FileSystemLoader(templates_path)
