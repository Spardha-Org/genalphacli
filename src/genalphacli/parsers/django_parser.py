"""Layer 2: Django/DRF AST-based route extraction."""

from __future__ import annotations

import ast
import logging
import re
from pathlib import Path

from genalphacli.models import (
    HttpMethod,
    ParamLocation,
    ParamType,
    ParsedRoute,
    ParseWarning,
    ResponseFormat,
    RouteParam,
    SourceLayer,
    resolve_type,
)

logger = logging.getLogger(__name__)

# Django path converter -> ParamType
_CONVERTER_TYPE_MAP: dict[str, ParamType] = {
    "int": ParamType.INTEGER,
    "str": ParamType.STRING,
    "slug": ParamType.STRING,
    "uuid": ParamType.STRING,
    "path": ParamType.STRING,
}

# Regex for <converter:name> or <name>
_PATH_PARAM_RE = re.compile(r"<(?:(\w+):)?(\w+)>")
# Regex for (?P<name>...) in re_path patterns
_REGEX_PARAM_RE = re.compile(r"\(\?P<(\w+)>")

# ViewSet base class -> list of (action_name, http_method, is_detail)
_VIEWSET_ACTION_MAP: dict[str, list[tuple[str, str, bool]]] = {
    "ModelViewSet": [
        ("list", "GET", False),
        ("create", "POST", False),
        ("retrieve", "GET", True),
        ("update", "PUT", True),
        ("partial_update", "PATCH", True),
        ("destroy", "DELETE", True),
    ],
    "ReadOnlyModelViewSet": [
        ("list", "GET", False),
        ("retrieve", "GET", True),
    ],
}

# DRF Mixin -> actions
_MIXIN_ACTION_MAP: dict[str, list[tuple[str, str, bool]]] = {
    "ListModelMixin": [("list", "GET", False)],
    "CreateModelMixin": [("create", "POST", False)],
    "RetrieveModelMixin": [("retrieve", "GET", True)],
    "UpdateModelMixin": [
        ("update", "PUT", True),
        ("partial_update", "PATCH", True),
    ],
    "DestroyModelMixin": [("destroy", "DELETE", True)],
}

# DRF generic view -> actions
_GENERIC_VIEW_MAP: dict[str, list[tuple[str, str, bool]]] = {
    "ListAPIView": [("list", "GET", False)],
    "CreateAPIView": [("create", "POST", False)],
    "RetrieveAPIView": [("retrieve", "GET", True)],
    "UpdateAPIView": [
        ("update", "PUT", True),
        ("partial_update", "PATCH", True),
    ],
    "DestroyAPIView": [("destroy", "DELETE", True)],
    "ListCreateAPIView": [
        ("list", "GET", False),
        ("create", "POST", False),
    ],
    "RetrieveUpdateAPIView": [
        ("retrieve", "GET", True),
        ("update", "PUT", True),
        ("partial_update", "PATCH", True),
    ],
    "RetrieveDestroyAPIView": [
        ("retrieve", "GET", True),
        ("destroy", "DELETE", True),
    ],
    "RetrieveUpdateDestroyAPIView": [
        ("retrieve", "GET", True),
        ("update", "PUT", True),
        ("partial_update", "PATCH", True),
        ("destroy", "DELETE", True),
    ],
}

_HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}

# Django generic CBV base classes -> default HTTP methods they handle
_DJANGO_CBV_METHODS: dict[str, list[str]] = {
    "ListView": ["GET"],
    "DetailView": ["GET"],
    "CreateView": ["GET", "POST"],
    "UpdateView": ["GET", "POST"],
    "DeleteView": ["GET", "POST"],
    "FormView": ["GET", "POST"],
    "TemplateView": ["GET"],
    "RedirectView": ["GET"],
    "LoginView": ["GET", "POST"],
    "LogoutView": ["GET", "POST"],
    "PasswordChangeView": ["GET", "POST"],
    "PasswordChangeDoneView": ["GET"],
    "PasswordResetView": ["GET", "POST"],
    "PasswordResetDoneView": ["GET"],
    "PasswordResetConfirmView": ["GET", "POST"],
    "PasswordResetCompleteView": ["GET"],
}

# All recognized Django CBV base class names (for _is_apiview / _is_cbv checks)
_DJANGO_CBV_BASES: set[str] = set(_DJANGO_CBV_METHODS.keys()) | {"View"}

_SKIP_PARAMS = {"self", "cls", "request", "format", "args", "kwargs"}


def _convert_django_path(route: str) -> tuple[str, list[tuple[str, ParamType]]]:
    """Convert Django path like 'users/<int:user_id>/' to ('/users/{user_id}', [(user_id, INTEGER)])."""
    params: list[tuple[str, ParamType]] = []

    def replace_match(m: re.Match) -> str:
        converter = m.group(1) or "str"
        name = m.group(2)
        param_type = _CONVERTER_TYPE_MAP.get(converter, ParamType.STRING)
        params.append((name, param_type))
        return f"{{{name}}}"

    converted = _PATH_PARAM_RE.sub(replace_match, route)
    # Normalize: strip trailing slash, ensure leading slash
    converted = "/" + converted.strip("/")
    return converted, params


def _convert_regex_path(pattern: str) -> tuple[str, list[tuple[str, ParamType]]]:
    """Convert regex path like '^users/(?P<pk>[0-9]+)/$' to ('/users/{pk}', [...])."""
    # Strip anchors
    cleaned = pattern.lstrip("^").rstrip("$").rstrip("/")

    params: list[tuple[str, ParamType]] = []
    names = _REGEX_PARAM_RE.findall(cleaned)
    for name in names:
        params.append((name, ParamType.STRING))

    # Replace named groups with {name}
    converted = re.sub(r"\(\?P<(\w+)>[^)]*\)", lambda m: f"{{{m.group(1)}}}", cleaned)
    # Strip remaining regex syntax roughly (exclude {} to preserve {name} placeholders)
    converted = re.sub(r"[\\^$+?*.()\[\]|]", "", converted)
    converted = "/" + converted.strip("/")
    return converted, params


def _extract_action_info(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[bool, list[str], str] | None:
    """Extract @action decorator info: (detail, methods, url_path) or None."""
    for decorator in node.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        func = decorator.func
        if isinstance(func, ast.Name) and func.id == "action":
            pass
        elif isinstance(func, ast.Attribute) and func.attr == "action":
            pass
        else:
            continue

        detail = False
        methods: list[str] = ["get"]
        url_path = node.name.replace("_", "-")

        for kw in decorator.keywords:
            if kw.arg == "detail" and isinstance(kw.value, ast.Constant):
                detail = bool(kw.value.value)
            elif kw.arg == "methods":
                if isinstance(kw.value, ast.List):
                    methods = [
                        elt.value.lower()
                        for elt in kw.value.elts
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                    ]
            elif kw.arg == "url_path" and isinstance(kw.value, ast.Constant):
                url_path = str(kw.value.value)

        # Positional: first is detail
        if decorator.args:
            first = decorator.args[0]
            if isinstance(first, ast.Constant):
                detail = bool(first.value)

        return detail, methods, url_path

    return None


def _call_func_name(call: ast.Call) -> str:
    """Get the simple function name from a Call node."""
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


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


def _path_params_to_route_params(path_params: list[tuple[str, ParamType]]) -> list[RouteParam]:
    """Convert path param tuples to RouteParam objects."""
    return [
        RouteParam(
            name=name,
            location=ParamLocation.PATH,
            param_type=ptype,
            raw_type=ptype.value,
            required=True,
        )
        for name, ptype in path_params
    ]


def _extract_func_params(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    path_params: list[tuple[str, ParamType]],
) -> list[RouteParam]:
    """Extract user-facing params from function signature (skipping request, self, etc.)."""
    params: list[RouteParam] = []
    path_param_names = {name for name, _ in path_params}
    path_param_types = {name: ptype for name, ptype in path_params}

    args = node.args.args
    defaults = node.args.defaults
    non_default_count = len(args) - len(defaults)

    for i, arg in enumerate(args):
        name = arg.arg
        if name in _SKIP_PARAMS:
            continue

        has_default = i >= non_default_count

        if name in path_param_names:
            # Use type from path converter if available
            ptype = path_param_types[name]
            raw_type = ptype.value
            if arg.annotation:
                raw_type = _annotation_to_str(arg.annotation)
                ptype = resolve_type(raw_type)
            params.append(RouteParam(
                name=name,
                location=ParamLocation.PATH,
                param_type=ptype,
                raw_type=raw_type,
                required=True,
            ))
        else:
            raw_type = "str"
            if arg.annotation:
                raw_type = _annotation_to_str(arg.annotation)
            ptype = resolve_type(raw_type)
            params.append(RouteParam(
                name=name,
                location=ParamLocation.QUERY,
                param_type=ptype,
                raw_type=raw_type,
                required=not has_default,
            ))

    return params


class _FileMetadataCollector(ast.NodeVisitor):
    """Phase 1: Scan a file to collect imports, class defs, and router registrations."""

    def __init__(self) -> None:
        # local_name -> dotted module path (e.g. "views" -> "api.views")
        self.imports: dict[str, str] = {}
        # class name -> ClassDef node
        self.classes: dict[str, ast.ClassDef] = {}
        # router variable names (e.g. "router")
        self.router_vars: set[str] = set()
        # router prefix (variable name) -> list of (prefix, viewset_name)
        self.router_registrations: list[tuple[str, str]] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            local = alias.asname or alias.name
            self.imports[local] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            local = alias.asname or alias.name
            self.imports[local] = f"{module}.{alias.name}" if module else alias.name
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.classes[node.name] = node
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        # Detect: router = DefaultRouter() or router = SimpleRouter()
        if (
            len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Call)
        ):
            var_name = node.targets[0].id
            call_name = _call_func_name(node.value)
            if call_name in ("DefaultRouter", "SimpleRouter"):
                self.router_vars.add(var_name)
        self.generic_visit(node)

    def visit_Expr(self, node: ast.Expr) -> None:
        if isinstance(node.value, ast.Call):
            self._check_router_register(node.value)
        self.generic_visit(node)

    def _check_router_register(self, call: ast.Call) -> None:
        """Detect router.register(prefix, ViewSet, ...) calls."""
        if not (isinstance(call.func, ast.Attribute) and call.func.attr == "register"):
            return
        if not (isinstance(call.func.value, ast.Name) and call.func.value.id in self.router_vars):
            return
        if len(call.args) < 2:
            return

        prefix_node = call.args[0]
        viewset_node = call.args[1]

        if not isinstance(prefix_node, ast.Constant):
            return

        prefix = str(prefix_node.value).strip("^$").strip("/")

        viewset_name = None
        if isinstance(viewset_node, ast.Name):
            viewset_name = viewset_node.id
        elif isinstance(viewset_node, ast.Attribute):
            viewset_name = viewset_node.attr

        if viewset_name:
            self.router_registrations.append((prefix, viewset_name))


def _get_viewset_actions(class_node: ast.ClassDef) -> list[tuple[str, str, bool]]:
    """Return standard actions for a ViewSet based on its base classes."""
    base_names = []
    for base in class_node.bases:
        if isinstance(base, ast.Name):
            base_names.append(base.id)
        elif isinstance(base, ast.Attribute):
            base_names.append(base.attr)

    actions: list[tuple[str, str, bool]] = []

    # Check known ViewSet types
    for base_name in base_names:
        if base_name in _VIEWSET_ACTION_MAP:
            actions.extend(_VIEWSET_ACTION_MAP[base_name])
        if base_name in _MIXIN_ACTION_MAP:
            actions.extend(_MIXIN_ACTION_MAP[base_name])
        if base_name in _GENERIC_VIEW_MAP:
            actions.extend(_GENERIC_VIEW_MAP[base_name])

    return actions


def _get_apiview_methods(class_node: ast.ClassDef) -> list[str]:
    """Return HTTP methods defined on an APIView subclass."""
    methods = []
    for item in class_node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if item.name in _HTTP_METHODS:
                methods.append(item.name.upper())
    return methods


def _is_viewset(class_node: ast.ClassDef) -> bool:
    """Check if a class is a ViewSet (not an APIView)."""
    for base in class_node.bases:
        name = ""
        if isinstance(base, ast.Name):
            name = base.id
        elif isinstance(base, ast.Attribute):
            name = base.attr
        if "ViewSet" in name or name in _MIXIN_ACTION_MAP:
            return True
    return False


def _is_apiview(class_node: ast.ClassDef) -> bool:
    """Check if a class is an APIView or Django CBV subclass."""
    for base in class_node.bases:
        name = ""
        if isinstance(base, ast.Name):
            name = base.id
        elif isinstance(base, ast.Attribute):
            name = base.attr
        if name in ("APIView", "View") or name.endswith("APIView") or name in _DJANGO_CBV_BASES:
            return True
    return False


def _get_cbv_default_methods(class_node: ast.ClassDef) -> list[str] | None:
    """Return default HTTP methods for a Django generic CBV based on its base classes.

    Returns None if the class is not a recognized generic CBV.
    """
    for base in class_node.bases:
        name = ""
        if isinstance(base, ast.Name):
            name = base.id
        elif isinstance(base, ast.Attribute):
            name = base.attr
        if name in _DJANGO_CBV_METHODS:
            return list(_DJANGO_CBV_METHODS[name])
    return None


def _get_api_view_methods_from_decorator(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str] | None:
    """Extract methods from @api_view(['GET', 'POST']) decorator. Returns None if not @api_view."""
    for decorator in func_node.decorator_list:
        if isinstance(decorator, ast.Call):
            func = decorator.func
            name = ""
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr

            if name != "api_view":
                continue

            if decorator.args and isinstance(decorator.args[0], ast.List):
                methods = []
                for elt in decorator.args[0].elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        methods.append(elt.value.upper())
                return methods

    return None


class _UrlPatternCollector:
    """Phase 2: Resolve urlpatterns into ParsedRoute objects for a single file."""

    def __init__(
        self,
        file_path: Path,
        repo_root: Path,
        prefix: str,
        all_files: list[Path],
        visited: set[str],
    ) -> None:
        self.file_path = file_path
        self.repo_root = repo_root
        self.prefix = prefix
        self.all_files = all_files
        self.visited = visited
        self.routes: list[ParsedRoute] = []

        # Metadata about this file (built in phase 1)
        self._meta: _FileMetadataCollector | None = None
        # local function/class name -> AST node
        self._funcs: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
        # AST cache: avoid re-parsing the same file multiple times
        self._ast_cache: dict[Path, ast.Module] = {}

    def collect(self) -> None:
        """Parse the file and extract routes."""
        key = str(self.file_path.resolve())
        if key in self.visited:
            return
        self.visited.add(key)

        try:
            source = self.file_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(self.file_path))
        except SyntaxError:
            logger.warning("Syntax error in %s, skipping", self.file_path)
            return

        # Phase 1: collect metadata
        meta = _FileMetadataCollector()
        meta.visit(tree)
        self._meta = meta

        # Collect top-level function defs
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._funcs[node.name] = node

        # Find urlpatterns assignments
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "urlpatterns":
                        self._process_urlpatterns(node.value)
            elif isinstance(node, ast.AugAssign):
                if isinstance(node.target, ast.Name) and node.target.id == "urlpatterns":
                    self._process_urlpatterns(node.value)

    def _process_urlpatterns(self, node: ast.expr) -> None:
        """Process a urlpatterns list node (or BinOp concatenation)."""
        if isinstance(node, ast.List):
            for elt in node.elts:
                if isinstance(elt, ast.Call):
                    self._process_path_call(elt)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            self._process_urlpatterns(node.left)
            self._process_urlpatterns(node.right)

    def _process_path_call(self, call: ast.Call, extra_prefix: str = "") -> None:
        """Process a single path(), re_path(), or include() call."""
        func_name = _call_func_name(call)

        if func_name not in ("path", "re_path", "url"):
            return

        if not call.args:
            return

        # First arg: the route pattern
        route_arg = call.args[0]
        if not isinstance(route_arg, ast.Constant):
            return
        route_str = str(route_arg.value)

        # Convert to normalized path
        if func_name in ("re_path", "url"):
            converted_path, path_params = _convert_regex_path(route_str)
        else:
            converted_path, path_params = _convert_django_path(route_str)

        full_prefix = self.prefix.rstrip("/") + extra_prefix
        full_path = full_prefix + converted_path
        if not full_path.startswith("/"):
            full_path = "/" + full_path
        # Deduplicate double slashes but keep single
        full_path = re.sub(r"//+", "/", full_path)

        if len(call.args) < 2:
            return

        # Second arg: the view
        view_arg = call.args[1]
        self._dispatch_view(view_arg, full_path, path_params, route_str)

    def _dispatch_view(
        self,
        view_arg: ast.expr,
        full_path: str,
        path_params: list[tuple[str, ParamType]],
        raw_route: str,
    ) -> None:
        """Dispatch view_arg to appropriate handler."""

        # Case 1: include(...)
        if isinstance(view_arg, ast.Call) and _call_func_name(view_arg) == "include":
            self._handle_include(view_arg, full_path)
            return

        # Case 2: SomeClass.as_view(...)
        if (
            isinstance(view_arg, ast.Call)
            and isinstance(view_arg.func, ast.Attribute)
            and view_arg.func.attr == "as_view"
        ):
            class_node_expr = view_arg.func.value
            class_name = None
            if isinstance(class_node_expr, ast.Name):
                class_name = class_node_expr.id
            elif isinstance(class_node_expr, ast.Attribute):
                class_name = class_node_expr.attr

            if class_name and self._meta:
                class_node = self._meta.classes.get(class_name)
                if class_node is None:
                    # Try resolving from imports
                    class_node = self._resolve_class_from_imports(class_name)

                if class_node is not None:
                    self._handle_class_view(class_node, full_path, path_params, view_arg)
                    return

        # Case 3: Direct function reference (e.g., views.my_func or my_func)
        func_name = None
        source_module = None

        if isinstance(view_arg, ast.Attribute):
            # views.func_name
            func_name = view_arg.attr
            if isinstance(view_arg.value, ast.Name):
                source_module = view_arg.value.id
        elif isinstance(view_arg, ast.Name):
            func_name = view_arg.id

        if func_name:
            # Look up the function node
            func_node = self._resolve_func(func_name, source_module)
            if func_node is not None:
                methods = _get_api_view_methods_from_decorator(func_node)
                if methods is None:
                    methods = ["GET"]
                for method_str in methods:
                    try:
                        http_method = HttpMethod(method_str)
                    except ValueError:
                        continue
                    params = _extract_func_params(func_node, path_params)
                    self.routes.append(ParsedRoute(
                        method=http_method,
                        path=full_path,
                        function_name=func_node.name,
                        description=ast.get_docstring(func_node) or "",
                        params=params,
                        response_format=ResponseFormat.JSON,
                        source_file=self.file_path,
                        source_layer=SourceLayer.AST,
                        confidence=0.95,
                    ))
            else:
                # Try resolving as a module-level assignment to .as_view()
                # e.g. index = BoardList.as_view() or write = login_required(BoardWrite.as_view())
                class_node = self._resolve_asview_assignment(func_name, source_module)
                if class_node is not None:
                    # Create a dummy as_view() Call node (no kwargs)
                    dummy_call = ast.Call(func=ast.Name(id="as_view"), args=[], keywords=[])
                    self._handle_class_view(class_node, full_path, path_params, dummy_call)

    def _handle_include(self, include_call: ast.Call, prefix_path: str) -> None:
        """Handle include("module.urls") or include(router.urls)."""
        if not include_call.args:
            return

        arg = include_call.args[0]

        # Case: include(router.urls) — expand router registrations
        if (
            isinstance(arg, ast.Attribute)
            and arg.attr == "urls"
            and isinstance(arg.value, ast.Name)
            and self._meta
            and arg.value.id in self._meta.router_vars
        ):
            self._expand_router_urls(prefix_path)
            return

        # Case: include("module.urls") — follow the module
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            module_path = arg.value
            target_file = self._resolve_module_to_file(module_path)
            if target_file:
                sub_collector = _UrlPatternCollector(
                    file_path=target_file,
                    repo_root=self.repo_root,
                    prefix=prefix_path,
                    all_files=self.all_files,
                    visited=self.visited,
                )
                sub_collector.collect()
                self.routes.extend(sub_collector.routes)
            return

        # Case: include(("module.urls", "app_name")) — tuple form
        if isinstance(arg, ast.Tuple) and arg.elts:
            first = arg.elts[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                module_path = first.value
                target_file = self._resolve_module_to_file(module_path)
                if target_file:
                    sub_collector = _UrlPatternCollector(
                        file_path=target_file,
                        repo_root=self.repo_root,
                        prefix=prefix_path,
                        all_files=self.all_files,
                        visited=self.visited,
                    )
                    sub_collector.collect()
                    self.routes.extend(sub_collector.routes)

    def _expand_router_urls(self, prefix_path: str) -> None:
        """Expand router.register() calls into routes."""
        if not self._meta:
            return

        for reg_prefix, viewset_name in self._meta.router_registrations:
            class_node = self._meta.classes.get(viewset_name)
            if class_node is None:
                class_node = self._resolve_class_from_imports(viewset_name)
            if class_node is None:
                continue

            # Get standard CRUD actions from base class
            standard_actions = _get_viewset_actions(class_node)
            source_file = self.file_path

            for action_name, http_method_str, is_detail in standard_actions:
                if is_detail:
                    path = f"{prefix_path.rstrip('/')}/{reg_prefix}/{'{pk}'}"
                else:
                    path = f"{prefix_path.rstrip('/')}/{reg_prefix}"

                path = re.sub(r"//+", "/", path)
                if not path.startswith("/"):
                    path = "/" + path

                # Find the method function in the class for params/docstring
                func_node = self._find_method_in_class(class_node, action_name)
                description = ""
                params: list[RouteParam] = []
                if func_node:
                    description = ast.get_docstring(func_node) or ""
                    pk_params = [("pk", ParamType.INTEGER)] if is_detail else []
                    params = _extract_func_params(func_node, pk_params)

                try:
                    http_method = HttpMethod(http_method_str)
                except ValueError:
                    continue

                self.routes.append(ParsedRoute(
                    method=http_method,
                    path=path,
                    function_name=action_name,
                    description=description,
                    params=params,
                    response_format=ResponseFormat.JSON,
                    source_file=source_file,
                    source_layer=SourceLayer.AST,
                    confidence=0.95,
                ))

            # Get @action decorators from the class
            self._expand_viewset_actions(class_node, prefix_path, reg_prefix, source_file)

    def _expand_viewset_actions(
        self,
        class_node: ast.ClassDef,
        prefix_path: str,
        reg_prefix: str,
        source_file: Path,
    ) -> None:
        """Expand @action decorators on a ViewSet."""
        for item in class_node.body:
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            action_info = _extract_action_info(item)
            if action_info is None:
                continue

            detail, methods, url_path_suffix = action_info

            if detail:
                path = f"{prefix_path.rstrip('/')}/{reg_prefix}/{'{pk}'}/{url_path_suffix}"
            else:
                path = f"{prefix_path.rstrip('/')}/{reg_prefix}/{url_path_suffix}"

            path = re.sub(r"//+", "/", path)
            if not path.startswith("/"):
                path = "/" + path

            for method_str in methods:
                try:
                    http_method = HttpMethod(method_str.upper())
                except ValueError:
                    continue

                pk_params = [("pk", ParamType.INTEGER)] if detail else []
                params = _extract_func_params(item, pk_params)

                self.routes.append(ParsedRoute(
                    method=http_method,
                    path=path,
                    function_name=item.name,
                    description=ast.get_docstring(item) or "",
                    params=params,
                    response_format=ResponseFormat.JSON,
                    source_file=source_file,
                    source_layer=SourceLayer.AST,
                    confidence=0.95,
                ))

    def _handle_class_view(
        self,
        class_node: ast.ClassDef,
        full_path: str,
        path_params: list[tuple[str, ParamType]],
        as_view_call: ast.Call,
    ) -> None:
        """Handle SomeView.as_view() — either APIView or ViewSet."""
        if _is_viewset(class_node):
            # ViewSet used with as_view() is unusual but possible; use action mapping kwarg
            action_map: dict[str, str] = {}
            for kw in as_view_call.keywords:
                if isinstance(kw.value, ast.Constant):
                    action_map[kw.arg] = kw.value.value
            if not action_map:
                # Default to standard ViewSet actions
                standard_actions = _get_viewset_actions(class_node)
                for action_name, http_method_str, is_detail in standard_actions:
                    try:
                        http_method = HttpMethod(http_method_str)
                    except ValueError:
                        continue
                    self.routes.append(ParsedRoute(
                        method=http_method,
                        path=full_path,
                        function_name=action_name,
                        params=_path_params_to_route_params(path_params),
                        response_format=ResponseFormat.JSON,
                        source_file=self.file_path,
                        source_layer=SourceLayer.AST,
                        confidence=0.95,
                    ))
            else:
                for http_method_str, action_name in action_map.items():
                    try:
                        http_method = HttpMethod(http_method_str.upper())
                    except ValueError:
                        continue
                    func_node = self._find_method_in_class(class_node, action_name)
                    description = ast.get_docstring(func_node) if func_node else ""
                    params = _extract_func_params(func_node, path_params) if func_node else _path_params_to_route_params(path_params)
                    self.routes.append(ParsedRoute(
                        method=http_method,
                        path=full_path,
                        function_name=action_name,
                        description=description or "",
                        params=params,
                        response_format=ResponseFormat.JSON,
                        source_file=self.file_path,
                        source_layer=SourceLayer.AST,
                        confidence=0.95,
                    ))
        else:
            # APIView / Django CBV subclass
            methods = _get_apiview_methods(class_node)
            if not methods:
                # Check if it's a Django generic CBV with known default methods
                cbv_methods = _get_cbv_default_methods(class_node)
                if cbv_methods:
                    methods = cbv_methods
                else:
                    methods = ["GET"]
            for method_str in methods:
                try:
                    http_method = HttpMethod(method_str)
                except ValueError:
                    continue
                # Find the method handler
                func_node = self._find_method_in_class(class_node, method_str.lower())
                description = ast.get_docstring(func_node) if func_node else ""
                params = _extract_func_params(func_node, path_params) if func_node else _path_params_to_route_params(path_params)
                self.routes.append(ParsedRoute(
                    method=http_method,
                    path=full_path,
                    function_name=class_node.name,
                    description=description or "",
                    params=params,
                    response_format=ResponseFormat.JSON,
                    source_file=self.file_path,
                    source_layer=SourceLayer.AST,
                    confidence=0.95,
                ))

    def _find_method_in_class(
        self, class_node: ast.ClassDef, method_name: str
    ) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
        for item in class_node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == method_name:
                return item
        return None

    def _resolve_func(
        self, func_name: str, source_module: str | None
    ) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
        """Find a function node — either local or from an imported module."""
        # Try local first
        if func_name in self._funcs:
            return self._funcs[func_name]

        # Try resolving from imports
        if source_module and self._meta:
            module_path = self._meta.imports.get(source_module)
            if module_path is None:
                # Try finding files named source_module
                module_path = source_module
            target_file = self._resolve_module_to_file(module_path)
            if target_file:
                return self._get_func_from_file(target_file, func_name)

        return None

    def _resolve_asview_assignment(
        self, name: str, source_module: str | None
    ) -> ast.ClassDef | None:
        """Resolve a module-level assignment like ``index = BoardList.as_view()``
        or ``write = login_required(BoardWrite.as_view())`` to its class node.

        Returns the ClassDef if found, else None.
        For external Django CBVs (e.g. LogoutView) where the class source isn't
        available, a synthetic ClassDef stub is returned.
        """
        target_file: Path | None = None

        if source_module and self._meta:
            module_path = self._meta.imports.get(source_module)
            if module_path is None:
                module_path = source_module
            target_file = self._resolve_module_to_file(module_path)
        else:
            # Look in current file
            target_file = self.file_path

        if target_file is None:
            return None

        tree = self._parse_file_cached(target_file)
        if tree is None:
            return None

        # Find assignment: name = ... where value contains .as_view()
        for node in ast.iter_child_nodes(tree):
            if not isinstance(node, ast.Assign):
                continue
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                continue
            if node.targets[0].id != name:
                continue

            # Unwrap the value to find the .as_view() call
            class_name_found = self._extract_class_from_asview_expr(node.value)
            if class_name_found:
                # Look up the class in the same file
                cls = self._get_class_from_file(target_file, class_name_found)
                if cls:
                    return cls
                # Try resolving from imports of that file
                meta = _FileMetadataCollector()
                meta.visit(tree)
                cls = meta.classes.get(class_name_found)
                if cls:
                    return cls

                # If the class is a known Django CBV imported from Django itself,
                # create a synthetic ClassDef stub so _handle_class_view works.
                if class_name_found in _DJANGO_CBV_BASES:
                    stub = ast.ClassDef(
                        name=class_name_found,
                        bases=[ast.Name(id=class_name_found, ctx=ast.Load())],
                        keywords=[],
                        body=[ast.Pass()],
                        decorator_list=[],
                    )
                    return stub

        return None

    @staticmethod
    def _extract_class_from_asview_expr(node: ast.expr) -> str | None:
        """Extract the class name from expressions like:
        - ``SomeClass.as_view()``
        - ``login_required(SomeClass.as_view())``
        - ``decorator(SomeClass.as_view())``

        Returns the class name string or None.
        """
        # Direct: SomeClass.as_view(...)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "as_view"
        ):
            cls_expr = node.func.value
            if isinstance(cls_expr, ast.Name):
                return cls_expr.id
            if isinstance(cls_expr, ast.Attribute):
                return cls_expr.attr
            return None

        # Wrapped: some_decorator(SomeClass.as_view(...))
        if isinstance(node, ast.Call) and node.args:
            # The first positional arg might be the .as_view() call
            for arg in node.args:
                result = _UrlPatternCollector._extract_class_from_asview_expr(arg)
                if result:
                    return result

        return None

    def _resolve_class_from_imports(self, class_name: str) -> ast.ClassDef | None:
        """Resolve a class name by looking in imported files.

        Handles two patterns:
        1. Direct import: `from .views import UserViewSet` -> local_name=UserViewSet
        2. Module import: `from . import views` -> local_name=views, class found in views module
        """
        if not self._meta:
            return None

        for local_name, module_path in self._meta.imports.items():
            # Pattern 1: direct import of the class
            if local_name == class_name or module_path.endswith(f".{class_name}"):
                # The module containing this class
                parent_module = ".".join(module_path.split(".")[:-1])
                target_file = self._resolve_module_to_file(parent_module)
                if target_file is None:
                    target_file = self._resolve_module_to_file(module_path)
                if target_file:
                    cls = self._get_class_from_file(target_file, class_name)
                    if cls:
                        return cls

        # Pattern 2: module import (e.g. `from . import views`) — search all module files
        for local_name, module_path in self._meta.imports.items():
            target_file = self._resolve_module_to_file(module_path)
            if target_file is None:
                # Try just the local_name as a file stem
                target_file = self._resolve_module_to_file(local_name)
            if target_file:
                cls = self._get_class_from_file(target_file, class_name)
                if cls:
                    return cls

        return None

    def _parse_file_cached(self, file_path: Path) -> ast.Module | None:
        """Return a cached AST for file_path, parsing only on first access."""
        if file_path in self._ast_cache:
            return self._ast_cache[file_path]
        try:
            source = file_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(file_path))
        except (SyntaxError, OSError):
            return None
        self._ast_cache[file_path] = tree
        return tree

    def _get_func_from_file(
        self, file_path: Path, func_name: str
    ) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
        """Return the named function from a file (uses AST cache)."""
        tree = self._parse_file_cached(file_path)
        if tree is None:
            return None
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
                return node
        return None

    def _get_class_from_file(self, file_path: Path, class_name: str) -> ast.ClassDef | None:
        """Return the named class from a file (uses AST cache)."""
        tree = self._parse_file_cached(file_path)
        if tree is None:
            return None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                return node
        return None

    def _resolve_module_to_file(self, module_path: str) -> Path | None:
        """Resolve a dotted module path to a file on disk."""
        if not module_path:
            return None

        # Convert dots to path separators and try variants
        parts = module_path.replace(".", "/")
        file_dir = self.file_path.parent
        candidates = [
            # Prefer relative to current file's directory (handles relative imports)
            file_dir / f"{parts}.py",
            file_dir / parts / "__init__.py",
            # Then try from repo root
            self.repo_root / f"{parts}.py",
            self.repo_root / parts / "__init__.py",
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        # Try each ancestor directory of file_dir up to (and including) repo_root.
        # This handles Django project layouts where apps are siblings of the
        # project config package, e.g. include('main.urls') from
        # tutorialproject/tutorialproject/urls.py finds tutorialproject/main/urls.py.
        current = file_dir.parent
        repo_resolved = self.repo_root.resolve()
        while current != current.parent:
            for suffix in (f"{parts}.py", f"{parts}/__init__.py"):
                candidate = current / suffix
                if candidate.exists():
                    return candidate
            # Stop once we've checked repo_root itself
            if current.resolve() == repo_resolved:
                break
            current = current.parent

        # Last resort: search by stem, preferring files in same directory
        last_part = module_path.split(".")[-1]
        same_dir_match = None
        other_match = None
        for f in self.all_files:
            if f.stem == last_part:
                if f.parent == file_dir:
                    same_dir_match = f
                elif other_match is None:
                    other_match = f

        return same_dir_match or other_match


class DjangoParser:
    """Extract API routes from Django/DRF source files using AST parsing."""

    @property
    def framework_name(self) -> str:
        return "django"

    def supported_extensions(self) -> list[str]:
        return [".py"]

    def parse(self, files: list[Path], repo_root: Path) -> list[ParsedRoute]:
        """Parse all given files and return extracted routes."""
        all_routes: list[ParsedRoute] = []
        visited: set[str] = set()

        # Find the root urls.py files (the ones that contain urlpatterns but aren't sub-modules)
        # We want to start from urls.py files at the top level and let include() recurse
        urls_files = [f for f in files if f.name == "urls.py"]
        non_urls_files = [f for f in files if f.name != "urls.py"]

        # Process urls.py files — find root ones (not included by others)
        included_modules: set[str] = set()

        # First pass: find which modules are include()'d
        for urls_file in urls_files:
            try:
                source = urls_file.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(source, filename=str(urls_file))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and _call_func_name(node) == "include":
                    if node.args and isinstance(node.args[0], ast.Constant):
                        included_modules.add(str(node.args[0].value))

        # Identify which urls.py files contain include() calls (likely root URLconfs)
        files_with_includes: list[Path] = []
        files_without_includes: list[Path] = []
        for urls_file in urls_files:
            try:
                source = urls_file.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(source, filename=str(urls_file))
            except SyntaxError:
                files_without_includes.append(urls_file)
                continue
            has_include = any(
                isinstance(n, ast.Call) and _call_func_name(n) == "include"
                for n in ast.walk(tree)
            )
            if has_include:
                files_with_includes.append(urls_file)
            else:
                files_without_includes.append(urls_file)

        # Process root URLconfs first (those with include() calls), then the rest.
        # The visited set prevents double-processing of files reached via include().
        for urls_file in files_with_includes + files_without_includes:
            collector = _UrlPatternCollector(
                file_path=urls_file,
                repo_root=repo_root,
                prefix="",
                all_files=files,
                visited=visited,
            )
            collector.collect()
            all_routes.extend(collector.routes)

        return all_routes


def parse_django(
    repo_root: Path, files: list[Path] | None = None
) -> tuple[list[ParsedRoute], list[ParseWarning]]:
    """Parse Django/DRF routes from a repository.

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

    parser = DjangoParser()
    routes = parser.parse(files, repo_root)
    return routes, warnings
