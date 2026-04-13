"""Layer 2: FastAPI AST-based route extraction.

Uses Python's ast module to extract routes from FastAPI decorators,
resolve function signatures, and handle include_router prefix composition
across files via import tracking.
"""

from __future__ import annotations

import ast
import logging
import re
from pathlib import Path

from genalphacli.models import (
    RESPONSE_CLASS_MAP,
    HttpMethod,
    ParamLocation,
    ParsedRoute,
    ParseWarning,
    ResponseFormat,
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

        # First pass: build a map of file_path -> prefix from include_router calls
        file_prefix_map = _build_file_prefix_map(files, repo_root)

        for file_path in files:
            try:
                source = file_path.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(source, filename=str(file_path))
            except SyntaxError:
                logger.warning("Syntax error in %s, skipping", file_path)
                continue

            # Determine prefix for this file from include_router mappings
            file_prefix = file_prefix_map.get(str(file_path.resolve()), "")

            extractor = _RouteExtractor(file_path, file_prefix)
            extractor.visit(tree)
            all_routes.extend(extractor.routes)

        return all_routes


def _build_file_prefix_map(files: list[Path], repo_root: Path) -> dict[str, str]:
    """Build a mapping from source file paths to their include_router prefixes.

    Scans all files for include_router() calls, resolves the module.router
    argument back to a source file using import statements, and maps:
        resolved_file_path -> prefix

    Handles patterns like:
        from app.routes import users
        app.include_router(users.router, prefix="/api/v1/users")
    """
    file_prefix_map: dict[str, str] = {}

    for file_path in files:
        try:
            source = file_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError:
            continue

        collector = _IncludeRouterCollector(file_path, files, repo_root)
        collector.visit(tree)
        file_prefix_map.update(collector.file_prefix_map)

    return file_prefix_map


class _IncludeRouterCollector(ast.NodeVisitor):
    """Collect include_router calls and resolve them to file paths with prefixes."""

    def __init__(self, file_path: Path, all_files: list[Path], repo_root: Path) -> None:
        self.file_path = file_path
        self.all_files = all_files
        self.repo_root = repo_root
        self.file_prefix_map: dict[str, str] = {}
        # Track imports: local_name -> module_path
        self.imports: dict[str, str] = {}
        # Track constants for variable prefix resolution
        self.constants: dict[str, str] = {}

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Track 'from X import Y' statements."""
        if node.module and node.names:
            for alias in node.names:
                local_name = alias.asname or alias.name
                # Store as module.submodule for resolution
                self.imports[local_name] = f"{node.module}.{alias.name}"
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Track string constants."""
        if (
            len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            self.constants[node.targets[0].id] = node.value.value
        self.generic_visit(node)

    def visit_Expr(self, node: ast.Expr) -> None:
        """Look for include_router() calls."""
        if isinstance(node.value, ast.Call):
            self._check_include_router(node.value)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Also check calls inside function bodies (e.g., create_app())."""
        self._check_include_router(node)
        self.generic_visit(node)

    def _check_include_router(self, call: ast.Call) -> None:
        if not (isinstance(call.func, ast.Attribute) and call.func.attr == "include_router"):
            return
        if not call.args:
            return

        router_arg = call.args[0]

        # Extract prefix from keyword args
        prefix = ""
        for kw in call.keywords:
            if kw.arg == "prefix":
                if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                    prefix = kw.value.value
                elif isinstance(kw.value, ast.Name) and kw.value.id in self.constants:
                    prefix = self.constants[kw.value.id]

        # Resolve router_arg to a file path
        resolved_file = self._resolve_router_to_file(router_arg)
        if resolved_file and prefix:
            self.file_prefix_map[str(resolved_file.resolve())] = prefix

    def _resolve_router_to_file(self, router_arg: ast.expr) -> Path | None:
        """Resolve a router argument (like `users.router` or `user_router`) to a file path."""

        # Pattern 1: module.router (e.g., users.router, activities.router)
        if (
            isinstance(router_arg, ast.Attribute)
            and router_arg.attr == "router"
            and isinstance(router_arg.value, ast.Name)
        ):
            module_name = router_arg.value.id
            # Check if this module was imported
            if module_name in self.imports:
                return self._module_to_file(self.imports[module_name])
            # Try as a relative filename
            return self._find_file_by_name(module_name)

        # Pattern 2: direct variable name (e.g., user_router)
        if isinstance(router_arg, ast.Name):
            var_name = router_arg.id
            # Check if imported: from routes.users import router as user_router
            if var_name in self.imports:
                return self._module_to_file(self.imports[var_name])

        return None

    def _module_to_file(self, module_path: str) -> Path | None:
        """Convert a dotted module path to a file path.

        e.g., 'app.entrypoints.http.routes.activities' -> find activities.py
        """
        # Try converting dots to path separators
        parts = module_path.split(".")
        module_name = parts[-1]  # The actual module/file name

        # Search all files for one whose stem matches the module name
        return self._find_file_by_name(module_name)

    def _find_file_by_name(self, name: str) -> Path | None:
        """Find a Python file by its stem name among all project files."""
        for f in self.all_files:
            if f.stem == name:
                return f
        return None


class _RouteExtractor(ast.NodeVisitor):
    """Extract routes from FastAPI decorator patterns."""

    def __init__(self, file_path: Path, file_prefix: str) -> None:
        self.file_path = file_path
        self.file_prefix = file_prefix
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

            # Build full path: include_router prefix + APIRouter prefix + route path
            full_path = ""
            if self.file_prefix:
                full_path += self.file_prefix.rstrip("/")
            if self._router_prefix:
                full_path += self._router_prefix.rstrip("/")
            full_path += path if path != "" else ""

            # Ensure path starts with /
            if full_path and not full_path.startswith("/"):
                full_path = "/" + full_path
            if not full_path:
                full_path = "/"

            # Extract parameters from function signature
            params = self._extract_params(node, full_path)

            # Get description from docstring
            description = ast.get_docstring(node) or ""

            # Extract response info from decorator kwargs
            resp_format, resp_model = _extract_response_from_decorator(decorator)

            # Also check return type annotation
            if not resp_model and node.returns:
                resp_model = _annotation_to_str(node.returns)

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
                    response_format=resp_format,
                    response_model=resp_model,
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
            # Skip 'self', 'cls', and common non-API params
            if name in ("self", "cls"):
                continue

            # Skip FastAPI dependency injection params — but recover
            # known standard form types (OAuth2PasswordRequestForm)
            if _is_dependency_param(arg, name):
                # OAuth2PasswordRequestForm is a standard FastAPI class
                # (fastapi.security) implementing RFC 6749 Section 4.3.
                # Its fields are spec-defined: username + password.
                # TODO: For future frameworks (Django, Express, Spring),
                # each parser should handle their own standard auth classes.
                # TODO: For custom Depends() classes, resolve the chain
                # by following the type to its __init__ params in source.
                type_name = _annotation_to_str(arg.annotation) if arg.annotation else ""
                if "OAuth2PasswordRequestForm" in type_name:
                    params.append(RouteParam(
                        name="username", location=ParamLocation.QUERY,
                        param_type=ParamType.STRING, raw_type="str", required=True,
                    ))
                    params.append(RouteParam(
                        name="password", location=ParamLocation.QUERY,
                        param_type=ParamType.STRING, raw_type="str", required=True,
                    ))
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


# Names that are almost always DI-injected, not user-facing
_DI_PARAM_NAMES = {
    "request",
    "response",
    "db",
    "session",
    "current_user",
    "background_tasks",
    "token",
    "authorization",
    "credentials",
}

# Type name suffixes/patterns that indicate DI
_DI_TYPE_SUFFIXES = ("Dep", "Dependency")


def _is_dependency_param(arg: ast.arg, name: str) -> bool:
    """Check if a function parameter is a FastAPI dependency injection param.

    Detects:
    - Known DI param names (session, db, current_user, etc.)
    - Params annotated with Depends(...)
    - Params with Annotated[X, Depends(...)] annotations
    - Type names ending in 'Dep' (convention: SessionDep, TokenDep)
    """
    # Check known DI names
    if name in _DI_PARAM_NAMES:
        return True

    annotation = arg.annotation
    if annotation is None:
        return False

    # Check for direct Depends() annotation: param: Depends(get_db)
    if isinstance(annotation, ast.Call):
        func = annotation.func
        if isinstance(func, ast.Name) and func.id == "Depends":
            return True
        if isinstance(func, ast.Attribute) and func.attr == "Depends":
            return True

    # Check for type names ending in 'Dep' (e.g., SessionDep, CurrentUser)
    type_name = _annotation_to_str(annotation)
    if type_name.endswith(_DI_TYPE_SUFFIXES):
        return True

    # Check for Annotated[X, Depends(...)] pattern
    if (
        isinstance(annotation, ast.Subscript)
        and isinstance(annotation.value, ast.Name)
        and annotation.value.id == "Annotated"
    ):
        # Walk the slice to find Depends() calls
        slice_node = annotation.slice
        if isinstance(slice_node, ast.Tuple):
            for elt in slice_node.elts:
                if isinstance(elt, ast.Call):
                    func = elt.func
                    if isinstance(func, ast.Name) and func.id == "Depends":
                        return True
                    if isinstance(func, ast.Attribute) and func.attr == "Depends":
                        return True

    # Check common DI type names that aren't user params
    return type_name in ("Request", "Response", "BackgroundTasks", "WebSocket")


def _extract_response_from_decorator(
    decorator: ast.Call,
) -> tuple[ResponseFormat, str]:
    """Extract response_class and response_model from a FastAPI decorator.

    Handles:
        @app.get("/path", response_class=HTMLResponse)
        @app.get("/path", response_model=UserOut)
        @app.get("/path", response_model=List[User])
    """
    resp_format = ResponseFormat.JSON
    resp_model = ""

    for kw in decorator.keywords:
        if kw.arg == "response_class":
            class_name = _annotation_to_str(kw.value)
            resp_format = RESPONSE_CLASS_MAP.get(class_name, ResponseFormat.JSON)

        elif kw.arg == "response_model":
            resp_model = _annotation_to_str(kw.value)

    return resp_format, resp_model


def _extract_path_params(path: str) -> set[str]:
    """Extract parameter names from a path string like /users/{user_id}."""
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
