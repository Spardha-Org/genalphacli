"""Pip package generator — produces an installable CLI from a CommandGraph."""

from __future__ import annotations

import ast
import json
import logging
import re
from pathlib import Path
from typing import Any

from genalphacli.generators import get_jinja_env
from genalphacli.models import (
    BuildConfig,
    CommandGraph,
    CommandParam,
    ParamType,
    Subcommand,
)

logger = logging.getLogger(__name__)

# Python type mapping for generated code
_PARAM_TYPE_TO_PYTHON: dict[ParamType, str] = {
    ParamType.STRING: "str",
    ParamType.INTEGER: "int",
    ParamType.BOOLEAN: "bool",
    ParamType.FLOAT: "float",
    ParamType.LIST: "str",
    ParamType.FILE: "str",
    ParamType.JSON: "str",
}

# Default values by type
_PARAM_TYPE_DEFAULTS: dict[ParamType, str] = {
    ParamType.STRING: '""',
    ParamType.INTEGER: "0",
    ParamType.BOOLEAN: "False",
    ParamType.FLOAT: "0.0",
    ParamType.LIST: '""',
    ParamType.FILE: '""',
    ParamType.JSON: '""',
}

# Dangerous AST node types to reject in generated code
_DANGEROUS_CALLS = {"eval", "exec", "__import__", "compile", "globals", "locals"}
_DANGEROUS_ATTRS = {"system", "popen", "call", "run", "Popen"}


def generate(graph: CommandGraph, config: BuildConfig, output_dir: Path) -> Path:
    """Generate a pip-installable CLI package from a CommandGraph.

    Returns the path to the generated package directory.
    """
    pkg_dir = output_dir / config.cli_name
    src_dir = pkg_dir / "src" / config.cli_name

    # Create directory structure
    src_dir.mkdir(parents=True, exist_ok=True)

    env = get_jinja_env()

    # Build template context
    context = _build_context(graph, config)

    # Render and write templates
    _render_template(env, "pip_package/pyproject.toml.j2", pkg_dir / "pyproject.toml", context)
    _render_template(env, "pip_package/client.py.j2", src_dir / "client.py", context)

    _render_template(env, "pip_package/cli.py.j2", src_dir / "cli.py", context)

    # Write __init__.py (no template needed)
    (src_dir / "__init__.py").write_text(f'"""Auto-generated CLI for {config.cli_name}."""\n')

    # Copy graph.json for reference
    (src_dir / "_graph.json").write_text(json.dumps(graph.model_dump(), indent=2, default=str))

    # Validate generated Python files
    for py_file in src_dir.glob("*.py"):
        _validate_generated_code(py_file)

    logger.info("Generated pip package at %s", pkg_dir)
    return pkg_dir


def _build_context(graph: CommandGraph, config: BuildConfig) -> dict[str, Any]:
    """Convert CommandGraph + BuildConfig into a Jinja2 template context."""
    commands = []
    for sub in graph.subcommands:
        cmd = _build_command_context(sub)
        commands.append(cmd)

    return {
        "cli_name": _sanitize(config.cli_name),
        "base_url": _sanitize(config.base_url),
        "auth_type": _sanitize(config.auth.type.value),
        "auth_env_var": _sanitize(config.auth.env_var or f"{config.cli_name.upper()}_TOKEN"),
        "commands": commands,
    }


def _build_command_context(sub: Subcommand) -> dict[str, Any]:
    """Build template context for a single command."""
    path_params = []
    query_params = []
    body_params = []

    for param in sub.params:
        p = _build_param_context(param)
        flag_prefix = param.flag.lstrip("-")
        p["flag_name"] = flag_prefix

        if param.flag == f"--{param.name.replace('_', '-')}" and _is_path_param(
            param.name, sub.endpoint
        ):
            path_params.append(p)
        elif sub.method.value in ("POST", "PUT", "PATCH") and not _is_path_param(
            param.name, sub.endpoint
        ):
            body_params.append(p)
        else:
            query_params.append(p)

    # Make function name valid Python identifier
    func_name = re.sub(r"[^a-z0-9_]", "_", sub.name.replace("-", "_"))
    if func_name[0].isdigit():
        func_name = f"cmd_{func_name}"

    return {
        "cli_name": sub.name,
        "func_name": func_name,
        "description": _sanitize(sub.description or f"{sub.method.value} {sub.endpoint}"),
        "method": sub.method.value,
        "endpoint_template": sub.endpoint,
        "path_params": path_params,
        "query_params": query_params,
        "body_params": body_params,
        "has_body_params": len(body_params) > 0,
    }


def _build_param_context(param: CommandParam) -> dict[str, Any]:
    """Build template context for a single parameter."""
    python_type = _PARAM_TYPE_TO_PYTHON.get(param.type, "str")
    default_value = _PARAM_TYPE_DEFAULTS.get(param.type, '""')

    if param.default is not None:
        default_value = repr(param.default)

    return {
        "name": _make_python_name(param.name),
        "python_type": python_type,
        "required": param.required,
        "description": _sanitize(param.description or param.name),
        "default_value": default_value,
    }


def _is_path_param(name: str, endpoint: str) -> bool:
    """Check if a parameter is a path parameter in the endpoint."""
    return f"{{{name}}}" in endpoint or f"{{{name.replace('_', '-')}}}" in endpoint


# Reserved names used by the generated CLI template — params with these names get suffixed
_RESERVED_PARAM_NAMES = {"raw_body", "pretty", "body", "data", "result", "params"}


def _make_python_name(name: str) -> str:
    """Convert a parameter name to a valid Python identifier.

    Avoids collisions with reserved template variable names.
    """
    name = re.sub(r"[^a-z0-9_]", "_", name.lower())
    if name[0].isdigit() or not name:
        name = f"p_{name}"
    if name in _RESERVED_PARAM_NAMES:
        name = f"{name}_val"
    return name


def _sanitize(value: str) -> str:
    """Sanitize a string for safe embedding in Jinja2 templates and Python code.

    Escapes triple-quotes, backslashes, and Jinja2 delimiters.
    """
    value = value.replace("\\", "\\\\")
    value = value.replace('"""', '\\"\\"\\"')
    value = value.replace("'''", "\\'\\'\\'")
    value = value.replace("{{", "{ {")
    value = value.replace("}}", "} }")
    value = value.replace("{%", "{ %")
    value = value.replace("%}", "% }")
    # Remove newlines that could break string literals
    value = value.replace("\n", " ").replace("\r", "")
    return value


def _render_template(
    env: Any, template_name: str, output_path: Path, context: dict[str, Any]
) -> str:
    """Render a Jinja2 template and write to disk."""
    template = env.get_template(template_name)
    content = template.render(**context)
    output_path.write_text(content)
    return content


def _validate_generated_code(path: Path) -> None:
    """Validate generated Python code for syntax and safety.

    Checks:
    1. Syntactic validity via ast.parse()
    2. No dangerous function calls (eval, exec, os.system, etc.)
    """
    source = path.read_text()

    # Syntax check
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as e:
        raise RuntimeError(f"Generated code has syntax error in {path}: {e}")

    # Safety check: walk AST for dangerous patterns
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            # Check for dangerous function names
            if isinstance(func, ast.Name) and func.id in _DANGEROUS_CALLS:
                raise RuntimeError(f"Generated code contains dangerous call '{func.id}' in {path}")
            # Check for dangerous method calls (os.system, subprocess.run, etc.)
            if isinstance(func, ast.Attribute) and func.attr in _DANGEROUS_ATTRS:
                raise RuntimeError(
                    f"Generated code contains dangerous call '{func.attr}' in {path}"
                )
