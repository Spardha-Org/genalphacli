"""Tests for data models."""

import pytest
from pydantic import ValidationError

from genalphacli.models import (
    AuthType,
    CommandGraph,
    CommandParam,
    HttpMethod,
    ParamLocation,
    ParamType,
    ParsedRoute,
    RouteParam,
    SourceLayer,
    Subcommand,
    resolve_type,
)


class TestEnums:
    def test_http_methods(self):
        assert HttpMethod.GET == "GET"
        assert HttpMethod.POST.value == "POST"

    def test_source_layer_ordering(self):
        assert SourceLayer.OPENAPI < SourceLayer.AST < SourceLayer.LLM

    def test_auth_types(self):
        assert AuthType.BEARER == "bearer"
        assert AuthType.NONE == "none"


class TestResolveType:
    def test_python_basic_types(self):
        assert resolve_type("str") == ParamType.STRING
        assert resolve_type("int") == ParamType.INTEGER
        assert resolve_type("bool") == ParamType.BOOLEAN
        assert resolve_type("float") == ParamType.FLOAT

    def test_generic_types(self):
        assert resolve_type("List[str]") == ParamType.LIST
        assert resolve_type("Optional[int]") == ParamType.STRING  # Optional base

    def test_unknown_defaults_to_json(self):
        assert resolve_type("SomeModel") == ParamType.JSON
        assert resolve_type("UserCreate") == ParamType.JSON

    def test_java_types(self):
        assert resolve_type("String") == ParamType.STRING
        assert resolve_type("Integer") == ParamType.INTEGER
        assert resolve_type("Long") == ParamType.INTEGER
        assert resolve_type("Double") == ParamType.FLOAT


class TestRouteParam:
    def test_basic_creation(self):
        param = RouteParam(name="user_id", location=ParamLocation.PATH)
        assert param.name == "user_id"
        assert param.param_type == ParamType.STRING  # default
        assert param.required is True

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            RouteParam(name="x", location=ParamLocation.QUERY, bogus="field")


class TestParsedRoute:
    def test_basic_creation(self):
        route = ParsedRoute(
            method=HttpMethod.GET,
            path="/users",
            function_name="list_users",
        )
        assert route.source_layer == SourceLayer.UNKNOWN
        assert route.confidence == 1.0

    def test_confidence_range_validation(self):
        with pytest.raises(ValidationError):
            ParsedRoute(
                method=HttpMethod.GET,
                path="/",
                function_name="x",
                confidence=1.5,
            )

        with pytest.raises(ValidationError):
            ParsedRoute(
                method=HttpMethod.GET,
                path="/",
                function_name="x",
                confidence=-0.1,
            )


class TestCommandGraph:
    def test_basic_graph(self):
        graph = CommandGraph(
            command="myapi",
            subcommands=[
                Subcommand(
                    name="list-users",
                    method=HttpMethod.GET,
                    endpoint="/users",
                    params=[
                        CommandParam(name="limit", flag="--limit", type=ParamType.INTEGER),
                    ],
                ),
            ],
        )
        assert graph.schema_version == "1.0.0"
        assert graph.command == "myapi"
        assert len(graph.subcommands) == 1
        assert graph.subcommands[0].params[0].flag == "--limit"

    def test_serialization_roundtrip(self):
        graph = CommandGraph(command="test")
        data = graph.model_dump()
        restored = CommandGraph(**data)
        assert restored == graph

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            CommandGraph(command="x", unknown_field="y")
