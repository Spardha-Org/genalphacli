"""Tests for the pipeline orchestrator."""

from pathlib import Path

from genalphacli.models import HttpMethod, ParsedRoute, SourceLayer
from genalphacli.pipeline import (
    index_files,
    merge_routes,
    normalize_path,
    routes_to_command_graph,
    run_pipeline,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestNormalizePath:
    def test_replaces_params(self):
        assert normalize_path("/users/{id}") == "/users/{}"

    def test_multiple_params(self):
        assert normalize_path("/users/{user_id}/posts/{post_id}") == "/users/{}/posts/{}"

    def test_strips_trailing_slash(self):
        assert normalize_path("/users/") == "/users"

    def test_root_path(self):
        assert normalize_path("/") == "/"


class TestMergeRoutes:
    def test_later_layer_wins(self):
        openapi_route = ParsedRoute(
            method=HttpMethod.GET,
            path="/users",
            function_name="from_openapi",
            source_layer=SourceLayer.OPENAPI,
        )
        ast_route = ParsedRoute(
            method=HttpMethod.GET,
            path="/users",
            function_name="from_ast",
            source_layer=SourceLayer.AST,
        )
        merged = merge_routes([openapi_route], [ast_route])
        assert len(merged) == 1
        assert merged[0].function_name == "from_ast"

    def test_different_methods_not_merged(self):
        get_route = ParsedRoute(method=HttpMethod.GET, path="/users", function_name="list")
        post_route = ParsedRoute(method=HttpMethod.POST, path="/users", function_name="create")
        merged = merge_routes([get_route], [post_route])
        assert len(merged) == 2

    def test_path_param_names_normalized(self):
        """Routes with different param names for same path should merge."""
        route1 = ParsedRoute(
            method=HttpMethod.GET,
            path="/users/{id}",
            function_name="r1",
            source_layer=SourceLayer.OPENAPI,
        )
        route2 = ParsedRoute(
            method=HttpMethod.GET,
            path="/users/{user_id}",
            function_name="r2",
            source_layer=SourceLayer.AST,
        )
        merged = merge_routes([route1], [route2])
        assert len(merged) == 1
        assert merged[0].function_name == "r2"  # later wins


class TestRoutesToCommandGraph:
    def test_basic_conversion(self):
        routes = [
            ParsedRoute(method=HttpMethod.GET, path="/users", function_name="list_users"),
        ]
        graph = routes_to_command_graph(routes, command_name="test")
        assert graph.command == "test"
        assert len(graph.subcommands) == 1
        assert graph.subcommands[0].name == "list-users"
        assert graph.subcommands[0].method == HttpMethod.GET

    def test_flag_name_generation(self):
        from genalphacli.models import ParamLocation, RouteParam

        routes = [
            ParsedRoute(
                method=HttpMethod.GET,
                path="/users",
                function_name="list_users",
                params=[RouteParam(name="user_id", location=ParamLocation.QUERY)],
            ),
        ]
        graph = routes_to_command_graph(routes)
        assert graph.subcommands[0].params[0].flag == "--user-id"


class TestIndexFiles:
    def test_indexes_python_files(self):
        idx = index_files(FIXTURES / "fastapi_simple")
        assert ".py" in idx
        assert len(idx[".py"]) == 1

    def test_indexes_json_files(self):
        idx = index_files(FIXTURES / "openapi_v3")
        assert ".json" in idx


class TestRunPipeline:
    def test_fastapi_simple(self):
        graph = run_pipeline(FIXTURES / "fastapi_simple", framework="fastapi")
        assert graph.metadata.total_routes == 5
        assert "AST" in graph.metadata.layer_counts

    def test_openapi_only(self):
        graph = run_pipeline(FIXTURES / "openapi_v3")
        assert graph.metadata.total_routes == 4
        assert "OPENAPI" in graph.metadata.layer_counts

    def test_command_name_customizable(self):
        graph = run_pipeline(FIXTURES / "fastapi_simple", command_name="myapi")
        assert graph.command == "myapi"
