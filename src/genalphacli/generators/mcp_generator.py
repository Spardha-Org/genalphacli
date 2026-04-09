"""MCP server generator — produces a FastMCP server package from a CommandGraph."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from genalphacli.generators import get_jinja_env
from genalphacli.generators.pip_generator import (
    _build_context,
    _render_template,
    _validate_generated_code,
)
from genalphacli.models import BuildConfig, CommandGraph

logger = logging.getLogger(__name__)


def generate(graph: CommandGraph, config: BuildConfig, output_dir: Path) -> Path:
    """Generate a FastMCP server package from a CommandGraph.

    Returns the path to the generated package directory.
    """
    mcp_name = f"{config.cli_name}_mcp"
    pkg_dir = output_dir / mcp_name
    src_dir = pkg_dir / "src" / mcp_name

    # Create directory structure
    src_dir.mkdir(parents=True, exist_ok=True)

    env = get_jinja_env()

    # Build template context (reuse from CLI generator)
    context = _build_context(graph, config)

    # Render MCP-specific templates
    _render_template(env, "mcp_package/pyproject.toml.j2", pkg_dir / "pyproject.toml", context)
    _render_template(env, "mcp_package/client.py.j2", src_dir / "client.py", context)
    _render_template(env, "mcp_package/server.py.j2", src_dir / "server.py", context)

    # Write __init__.py
    (src_dir / "__init__.py").write_text(f'"""MCP server for {config.cli_name}."""\n')

    # Copy graph.json for reference
    (src_dir / "_graph.json").write_text(json.dumps(graph.model_dump(), indent=2, default=str))

    # Validate generated Python files
    for py_file in src_dir.glob("*.py"):
        _validate_generated_code(py_file)

    logger.info("Generated MCP server package at %s", pkg_dir)
    return pkg_dir


def _get_mcp_server_command(cli_name: str, pkg_path: Path) -> dict:
    """Build the command config for launching the MCP server.

    Uses absolute paths since Claude Desktop/Cursor don't inherit shell PATH.
    Prefers 'uv run' (handles venvs, avoids macOS sandbox permission issues).
    Falls back to 'python -m' if uv is not available.
    """
    import platform
    import shutil

    resolved_path = str(pkg_path.resolve())
    uv_path = shutil.which("uv")

    if uv_path:
        return {
            "command": uv_path,
            "args": ["--directory", resolved_path, "run", f"{cli_name}-mcp"],
        }

    # Fallback: use python directly
    python_path = shutil.which("python3") or shutil.which("python") or "python3"
    server_module = f"{cli_name}_mcp.server"

    if platform.system() == "Windows":
        python_path = shutil.which("python") or "python"

    return {
        "command": python_path,
        "args": ["-m", server_module],
    }


def get_claude_desktop_config(
    cli_name: str, base_url: str, auth_env_var: str, pkg_path: Path
) -> dict:
    """Generate the Claude Desktop config snippet for this MCP server.

    Auto-detects OS and available tools (uv/python) to build the right
    command config with absolute paths.
    """
    cmd = _get_mcp_server_command(cli_name, pkg_path)

    return {
        "mcpServers": {
            cli_name: {
                **cmd,
                "env": {
                    auth_env_var: f"${{env:{auth_env_var}}}",
                    f"{cli_name.upper()}_BASE_URL": base_url,
                },
            }
        }
    }


def find_claude_desktop_config() -> Path | None:
    """Find the Claude Desktop config file on this system."""
    import platform

    system = platform.system()
    home = Path.home()

    candidates = []
    if system == "Darwin":
        candidates.append(
            home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        )
    elif system == "Windows":
        appdata = Path(import_env("APPDATA", ""))
        if appdata:
            candidates.append(appdata / "Claude" / "claude_desktop_config.json")
    elif system == "Linux":
        candidates.append(home / ".config" / "claude" / "claude_desktop_config.json")

    for path in candidates:
        if path.is_file():
            return path

    return None


def import_env(name: str, default: str) -> str:
    """Read an environment variable."""
    import os

    return os.environ.get(name, default)


def register_with_claude_desktop(
    config_path: Path, cli_name: str, base_url: str, auth_env_var: str, pkg_path: Path
) -> bool:
    """Add this MCP server to Claude Desktop's config file.

    Returns True if successfully registered, False otherwise.
    """
    try:
        existing = json.loads(config_path.read_text())
    except (json.JSONDecodeError, OSError):
        return False

    if "mcpServers" not in existing:
        existing["mcpServers"] = {}

    cmd = _get_mcp_server_command(cli_name, pkg_path)
    existing["mcpServers"][cli_name] = {
        **cmd,
        "env": {
            auth_env_var: f"${{env:{auth_env_var}}}",
            f"{cli_name.upper()}_BASE_URL": base_url,
        },
    }

    config_path.write_text(json.dumps(existing, indent=2))
    return True
