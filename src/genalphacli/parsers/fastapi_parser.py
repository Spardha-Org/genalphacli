"""Layer 2: FastAPI AST-based route extraction.

Uses Python's ast module to extract routes from FastAPI decorators,
resolve function signatures, and handle include_router prefix composition.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path

from genalphacli.models import (
    HttpMethod,
    ParamLocation,
    ParsedRoute,
    ParseWarning,
    RouteParam,
    SourceLayer,
    resolve_type,
)

logger = logging.getLogger(__name__)

FASTAPI_METHODS = {"get", "post", "put", "delete", "patch", "head", "options"}


class FastApiParser:
    """Extract API routes from FastAPI source files using AST parsing."""

    @property
    def framework_name(self) -> str:
        return "fastapi"

    def supported_extensions(self) -> list[str]:
        return [".py"]

    def parse(self, files: list[Path], repo_root: Path) -> list[ParsedRoute]:
        """Parse all given files and return extracted routes."""
        all_routes: list[ParsedRoute] = []
        # First pass: collect router prefixes from include_router calls
        prefix_map = self._collect_router_prefixes(files, repo_root)

        for file_path in files:
            try:
                source = file_path.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(source, filename=str(file_path))
            except SyntaxError:
                logger.warning("Syntax error in %s, skipping", file_path)
                continue

            extractor = _RouteExtractor(file_path, prefix_map, repo_root)
            extractor.visit(tree)
            all_routes.extend(extractor.routes)

        return all_routes

    def _collect_router_prefixes(self, files: list[Path], repo_root: Path) -> dict[str, str]:
        """Collect prefix mappings from include_router calls.

        Returns a dict mapping module-level variable names to their prefixes.
        This handles patterns like:
            app.include_router(user_router, prefix="/api/v1/users")
        """
        prefixes: dict[str, str] = {}

        for file_path in files:
            try:
                source = file_path.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(source, filename=str(file_path))
            except SyntaxError:
                continue

            collector = _PrefixCollector(file_path)
            collector.visit(tree)
            prefixes.update(collector.prefixes)

        return prefixes


class _PrefixCollector(ast.NodeVisitor):
    """Collect prefix mappings from include_router and constant assignments."""

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.prefixes: dict[str, str] = {}
        self.constants: dict[str, str] = {}

    def visit_Assign(self, node: ast.Assign) -> None:
        """Track string constant assignments for prefix resolution."""
        if (
            len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            self.constants[node.targets[0].id] = node.value.value
        self.generic_visit(node)

    def visit_Expr(self, node: ast.Expr) -> None:
        """Look for app.include_router(router, prefix="/path") calls."""
        if isinstance(node.value, ast.Call):
            self._check_include_router(node.value)
        self.generic_visit(node)

    def _check_include_router(self, call: ast.Call) -> None:
        if not (isinstance(call.func, ast.Attribute) and call.func.attr == "include_router"):
            return

        # Get the router argument (first positional arg)
        if not call.args:
            return

        router_arg = call.args[0]
        router_name = ""
        if isinstance(router_arg, ast.Name):
            router_name = router_arg.id
        elif isinstance(router_arg, ast.Attribute):
            router_name = router_arg.attr

        # Get prefix from keyword args
        prefix = ""
        for kw in call.keywords:
            if kw.arg == "prefix":
                if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                    prefix = kw.value.value
                elif isinstance(kw.value, ast.Name) and kw.value.id in self.constants:
                    prefix = self.constants[kw.value.id]

        if router_name and prefix:
            # Key by file:router_name for uniqueness
            key = f"{self.file_path.stem}:{router_name}"
            self.prefixes[key] = prefix


class _RouteExtractor(ast.NodeVisitor):
    """Extract routes from FastAPI decorator patterns."""

    def __init__(
        self,
        file_path: Path,
        prefix_map: dict[str, str],
        repo_root: Path,
    ) -> None:
        self.file_path = file_path
        self.prefix_map = prefix_map
        self.repo_root = repo_root
        self.routes: list[ParsedRoute] = []
        self.constants: dict[str, str] = {}
        self._router_prefix: str = ""

    def visit_Assign(self, node: ast.Assign) -> None:
        """Track string constants and APIRouter prefix assignments."""
        if (
            len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            self.constants[node.targets[0].id] = node.value.value

        # Track APIRouter(prefix="/prefix") assignments
        if (
            len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Call)
        ):
            self._check_router_assignment(node.targets[0].id, node.value)

        self.generic_visit(node)

    def _check_router_assignment(self, var_name: str, call: ast.Call) -> None:
        """Check if this is an APIRouter(prefix=...) call."""
        func = call.func
        is_api_router = (isinstance(func, ast.Name) and func.id == "APIRouter") or (
            isinstance(func, ast.Attribute) and func.attr == "APIRouter"
        )

        if not is_api_router:
            return

        for kw in call.keywords:
            if (
                kw.arg == "prefix"
                and isinstance(kw.value, ast.Constant)
                and isinstance(kw.value.value, str)
            ):
                self._router_prefix = kw.value.value

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._process_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._process_function(node)
        self.generic_visit(node)

    def _process_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Extract route info from function decorators."""
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if not isinstance(decorator.func, ast.Attribute):
                continue

            method_name = decorator.func.attr
            if method_name not in FASTAPI_METHODS:
                continue

            # Extract path from first argument
            path = self._extract_path(decorator)
            if path is None:
                continue

            # Apply router prefix
            full_path = self._router_prefix.rstrip("/") + path if self._router_prefix else path

            # Check prefix_map for include_router prefix
            for key, prefix in self.prefix_map.items():
                if key.endswith(f":{self.file_path.stem}_router") or key.endswith(":router"):
                    full_path = prefix.rstrip("/") + full_path
                    break

            # Extract parameters from function signature
            params = self._extract_params(node, full_path)

            # Get description from docstring
            description = ast.get_docstring(node) or ""

            try:
                http_method = HttpMethod(method_name.upper())
            except ValueError:
                continue

            self.routes.append(
                ParsedRoute(
                    method=http_method,
                    path=full_path,
                    function_name=node.name,
                    description=description,
                    params=params,
                    source_file=self.file_path,
                    source_layer=SourceLayer.AST,
                    confidence=0.95,
                )
            )

    def _extract_path(self, decorator: ast.Call) -> str | None:
        """Extract the path string from a decorator call."""
        if not decorator.args:
            return None

        arg = decorator.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
        if isinstance(arg, ast.Name) and arg.id in self.constants:
            return self.constants[arg.id]
        return None

    def _extract_params(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, path: str
    ) -> list[RouteParam]:
        """Extract parameters from function signature."""
        params: list[RouteParam] = []
        path_params = _extract_path_params(path)

        for arg in node.args.args:
            name = arg.arg
            # Skip 'self', 'cls', 'request', 'response', 'db'
            if name in ("self", "cls", "request", "response", "db"):
                continue

            # Determine type from annotation
            raw_type = "str"
            if arg.annotation:
                raw_type = _annotation_to_str(arg.annotation)

            param_type = resolve_type(raw_type)

            # Determine location
            if name in path_params:
                location = ParamLocation.PATH
                required = True
            else:
                location = ParamLocation.QUERY
                required = True  # Default; overridden below if has default

            # Check for default values
            defaults = node.args.defaults
            non_default_count = len(node.args.args) - len(defaults)
            arg_index = node.args.args.index(arg)
            has_default = arg_index >= non_default_count

            if has_default and location != ParamLocation.PATH:
                required = False

            params.append(
                RouteParam(
                    name=name,
                    location=location,
                    param_type=param_type,
                    raw_type=raw_type,
                    required=required,
                )
            )

        return params


def _extract_path_params(path: str) -> set[str]:
    """Extract parameter names from a path string like /users/{user_id}."""
    import re

    return set(re.findall(r"\{(\w+)\}", path))


def _annotation_to_str(annotation: ast.expr) -> str:
    """Convert an AST annotation node to a string representation."""
    if isinstance(annotation, ast.Name):
        return annotation.id
    if isinstance(annotation, ast.Constant):
        return str(annotation.value)
    if isinstance(annotation, ast.Attribute):
        return annotation.attr
    if isinstance(annotation, ast.Subscript):
        base = _annotation_to_str(annotation.value)
        return f"{base}[...]"
    return "str"


def parse_fastapi(
    repo_root: Path, files: list[Path] | None = None
) -> tuple[list[ParsedRoute], list[ParseWarning]]:
    """Parse FastAPI routes from a repository.

    If files is None, discovers .py files automatically.
    """
    warnings: list[ParseWarning] = []

    if files is None:
        files = [
            p
            for p in repo_root.rglob("*.py")
            if not p.is_symlink()
            and ".venv" not in p.parts
            and "__pycache__" not in p.parts
            and "node_modules" not in p.parts
        ]

    parser = FastApiParser()
    routes = parser.parse(files, repo_root)
    return routes, warnings
