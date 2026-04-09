"""Extract Pydantic model schemas from Python source files.

Parses class definitions that inherit from BaseModel (or similar),
extracts field names, types, and defaults to build JSON-serializable schemas.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path

from genalphacli.models import resolve_type

logger = logging.getLogger(__name__)

# Base classes that indicate a Pydantic model
_PYDANTIC_BASES = {"BaseModel", "BaseSettings", "BaseConfig"}


def extract_models(files: list[Path]) -> dict[str, dict]:
    """Extract all Pydantic model schemas from a list of Python files.

    Returns a dict mapping model name to schema:
    {
        "UserOut": {
            "name": "UserOut",
            "fields": {
                "id": {"type": "integer", "required": True},
                "name": {"type": "string", "required": True},
                "email": {"type": "string", "required": True},
                "role": {"type": "string", "required": False, "default": "user"},
            }
        }
    }
    """
    models: dict[str, dict] = {}

    for file_path in files:
        try:
            source = file_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            if not _is_pydantic_model(node):
                continue

            schema = _extract_class_schema(node)
            if schema:
                models[node.name] = schema

    return models


def resolve_response_model(model_name: str, model_registry: dict[str, dict]) -> dict | None:
    """Resolve a response_model string to a full schema object.

    Handles:
        "UserOut"           -> direct lookup
        "list[...]"         -> try to extract inner type
        "List[UserOut]"     -> unwrap and lookup UserOut
        "dict[...]"         -> return generic dict schema
    """
    if not model_name:
        return None

    # Direct lookup
    if model_name in model_registry:
        return model_registry[model_name]

    # Handle List[Model] / list[Model]
    inner = _unwrap_generic(model_name)
    if inner and inner in model_registry:
        return {
            "name": model_name,
            "type": "array",
            "items": model_registry[inner],
        }

    # Handle generic annotations like "list[...]", "dict[...]"
    if model_name.startswith(("list[", "List[")):
        return {"name": model_name, "type": "array", "items": None}
    if model_name.startswith(("dict[", "Dict[")):
        return {"name": model_name, "type": "object"}

    # Not found in registry
    return {"name": model_name, "type": "unknown"}


def _is_pydantic_model(node: ast.ClassDef) -> bool:
    """Check if a class inherits from a Pydantic base class."""
    for base in node.bases:
        base_name = ""
        if isinstance(base, ast.Name):
            base_name = base.id
        elif isinstance(base, ast.Attribute):
            base_name = base.attr
        if base_name in _PYDANTIC_BASES:
            return True
    return False


def _extract_class_schema(node: ast.ClassDef) -> dict:
    """Extract field information from a Pydantic model class definition."""
    fields: dict[str, dict] = {}

    for stmt in node.body:
        # Skip non-annotation assignments (methods, model_config, etc.)
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            field_name = stmt.target.id

            # Skip private/internal fields
            if field_name.startswith("_") or field_name == "model_config":
                continue

            # Get type annotation
            raw_type = _annotation_to_type_str(stmt.annotation)
            param_type = resolve_type(raw_type)

            # Check if field has a default value
            has_default = stmt.value is not None
            required = not has_default

            # Check for Optional[X] which implies not required
            if raw_type.startswith(("Optional", "None |", "| None")):
                required = False

            field_info: dict = {
                "type": param_type.value,
                "required": required,
            }

            # Extract default value if it's a simple constant
            if has_default and isinstance(stmt.value, ast.Constant):
                field_info["default"] = stmt.value.value

            # Check for Field(default=...) pattern
            if has_default and isinstance(stmt.value, ast.Call):
                default_val = _extract_field_default(stmt.value)
                if default_val is not None:
                    field_info["default"] = default_val

            fields[field_name] = field_info

    return {"name": node.name, "fields": fields}


def _annotation_to_type_str(annotation: ast.expr) -> str:
    """Convert an AST type annotation to a readable string."""
    if isinstance(annotation, ast.Name):
        return annotation.id
    if isinstance(annotation, ast.Constant):
        return str(annotation.value)
    if isinstance(annotation, ast.Attribute):
        return annotation.attr
    if isinstance(annotation, ast.Subscript):
        base = _annotation_to_type_str(annotation.value)
        inner = _annotation_to_type_str(annotation.slice)
        return f"{base}[{inner}]"
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        # Handle X | None syntax
        left = _annotation_to_type_str(annotation.left)
        right = _annotation_to_type_str(annotation.right)
        return f"{left} | {right}"
    if isinstance(annotation, ast.Tuple):
        parts = [_annotation_to_type_str(e) for e in annotation.elts]
        return ", ".join(parts)
    return "str"


def _extract_field_default(call: ast.Call) -> object | None:
    """Extract default value from Field(default=X) or Field(X)."""
    # Check keyword: Field(default="value")
    for kw in call.keywords:
        if kw.arg == "default" and isinstance(kw.value, ast.Constant):
            return kw.value.value
    # Check first positional arg: Field("value")
    if call.args and isinstance(call.args[0], ast.Constant):
        return call.args[0].value
    return None


def _unwrap_generic(type_str: str) -> str | None:
    """Unwrap List[X] or list[X] to return X."""
    for prefix in ("List[", "list[", "Sequence[", "Set[", "set["):
        if type_str.startswith(prefix) and type_str.endswith("]"):
            return type_str[len(prefix) : -1].strip()
    return None
