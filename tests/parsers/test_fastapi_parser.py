"""Tests for FastAPI AST parser."""

from pathlib import Path

from genalphacli.models import HttpMethod, ParamLocation, ParamType, SourceLayer
from genalphacli.parsers.fastapi_parser import parse_fastapi

FIXTURES = Path(__file__).parent.parent / "fixtures"


class TestFastapiSimple:
    def test_extracts_all_routes(self):
        routes, warnings = parse_fastapi(FIXTURES / "fastapi_simple")
        assert len(routes) == 5
        assert len(warnings) == 0

    def test_get_route(self):
        routes, _ = parse_fastapi(FIXTURES / "fastapi_simple")
        list_users = next(r for r in routes if r.function_name == "list_users")
        assert list_users.method == HttpMethod.GET
        assert list_users.path == "/users"
        assert list_users.source_layer == SourceLayer.AST

    def test_path_params_detected(self):
        routes, _ = parse_fastapi(FIXTURES / "fastapi_simple")
        get_user = next(r for r in routes if r.function_name == "get_user")
        assert get_user.path == "/users/{user_id}"
        assert len(get_user.params) == 1
        assert get_user.params[0].name == "user_id"
        assert get_user.params[0].location == ParamLocation.PATH
        assert get_user.params[0].param_type == ParamType.INTEGER

    def test_query_params_with_defaults(self):
        routes, _ = parse_fastapi(FIXTURES / "fastapi_simple")
        list_users = next(r for r in routes if r.function_name == "list_users")
        assert len(list_users.params) == 2

        limit = next(p for p in list_users.params if p.name == "limit")
        assert limit.location == ParamLocation.QUERY
        assert limit.required is False  # has default

    def test_async_functions_extracted(self):
        routes, _ = parse_fastapi(FIXTURES / "fastapi_simple")
        create_user = next(r for r in routes if r.function_name == "create_user")
        assert create_user.method == HttpMethod.POST

    def test_docstrings_as_description(self):
        routes, _ = parse_fastapi(FIXTURES / "fastapi_simple")
        root = next(r for r in routes if r.function_name == "root")
        assert root.description == "Root endpoint."

    def test_type_hints_resolved(self):
        routes, _ = parse_fastapi(FIXTURES / "fastapi_simple")
        create_user = next(r for r in routes if r.function_name == "create_user")
        name_param = next(p for p in create_user.params if p.name == "name")
        assert name_param.param_type == ParamType.STRING
        age_param = next(p for p in create_user.params if p.name == "age")
        assert age_param.param_type == ParamType.INTEGER


class TestFastapiComplex:
    def test_router_prefix_applied(self):
        routes, _ = parse_fastapi(FIXTURES / "fastapi_complex")
        router_routes = [r for r in routes if r.function_name != "health"]
        assert all("/users" in r.path for r in router_routes)

    def test_health_endpoint_found(self):
        routes, _ = parse_fastapi(FIXTURES / "fastapi_complex")
        health = next(r for r in routes if r.function_name == "health")
        assert health.path == "/health"
        assert health.method == HttpMethod.GET
