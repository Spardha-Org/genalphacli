"""Tests for OpenAPI parser."""

from pathlib import Path

from genalphacli.models import HttpMethod, ParamLocation, SourceLayer
from genalphacli.parsers.openapi_parser import find_spec_files, parse_openapi

FIXTURES = Path(__file__).parent.parent / "fixtures"


class TestFindSpecFiles:
    def test_finds_openapi_json(self):
        files = find_spec_files(FIXTURES / "openapi_v3")
        assert len(files) == 1
        assert files[0].name == "openapi.json"

    def test_empty_when_no_specs(self):
        files = find_spec_files(FIXTURES / "fastapi_simple")
        assert len(files) == 0


class TestParseOpenapi:
    def test_parses_v3_spec(self):
        routes, warnings = parse_openapi(FIXTURES / "openapi_v3")
        assert len(warnings) == 0
        assert len(routes) == 4

        # Check route details
        get_users = next(r for r in routes if r.function_name == "list_users")
        assert get_users.method == HttpMethod.GET
        assert get_users.path == "/users"
        assert get_users.source_layer == SourceLayer.OPENAPI
        assert get_users.confidence == 1.0
        assert len(get_users.params) == 2

        # Check param details
        limit_param = next(p for p in get_users.params if p.name == "limit")
        assert limit_param.location == ParamLocation.QUERY
        assert limit_param.raw_type == "integer"

    def test_extracts_path_params(self):
        routes, _ = parse_openapi(FIXTURES / "openapi_v3")
        get_user = next(r for r in routes if r.function_name == "get_user")
        assert get_user.path == "/users/{user_id}"

        user_id_param = get_user.params[0]
        assert user_id_param.name == "user_id"
        assert user_id_param.location == ParamLocation.PATH
        assert user_id_param.required is True

    def test_extracts_request_body(self):
        routes, _ = parse_openapi(FIXTURES / "openapi_v3")
        create_user = next(r for r in routes if r.function_name == "create_user")
        assert create_user.method == HttpMethod.POST

        body_params = [p for p in create_user.params if p.location == ParamLocation.BODY]
        assert len(body_params) == 3
        names = {p.name for p in body_params}
        assert names == {"name", "email", "age"}

        name_param = next(p for p in body_params if p.name == "name")
        assert name_param.required is True

    def test_returns_empty_for_no_specs(self):
        routes, warnings = parse_openapi(FIXTURES / "fastapi_simple")
        assert len(routes) == 0
        assert len(warnings) == 0
