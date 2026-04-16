"""Tests for Django/DRF AST parser."""

from pathlib import Path

from genalphacli.models import HttpMethod, ParamLocation, ParamType, SourceLayer
from genalphacli.parsers.django_parser import parse_django

FIXTURES = Path(__file__).parent.parent / "fixtures"


class TestDjangoSimple:
    def test_extracts_all_routes(self):
        routes, warnings = parse_django(FIXTURES / "django_simple")
        assert len(routes) == 5
        assert len(warnings) == 0

    def test_get_route(self):
        routes, _ = parse_django(FIXTURES / "django_simple")
        list_users = next(r for r in routes if r.function_name == "list_users")
        assert list_users.method == HttpMethod.GET
        assert list_users.path == "/users"
        assert list_users.source_layer == SourceLayer.AST

    def test_path_params_detected(self):
        routes, _ = parse_django(FIXTURES / "django_simple")
        get_user = next(r for r in routes if r.function_name == "get_user")
        assert get_user.path == "/users/{user_id}"
        assert len(get_user.params) == 1
        assert get_user.params[0].name == "user_id"
        assert get_user.params[0].location == ParamLocation.PATH
        assert get_user.params[0].param_type == ParamType.INTEGER

    def test_query_params_with_defaults(self):
        routes, _ = parse_django(FIXTURES / "django_simple")
        list_users = next(r for r in routes if r.function_name == "list_users")
        assert len(list_users.params) == 2

        limit = next(p for p in list_users.params if p.name == "limit")
        assert limit.location == ParamLocation.QUERY
        assert limit.required is False

    def test_docstrings_as_description(self):
        routes, _ = parse_django(FIXTURES / "django_simple")
        root = next(r for r in routes if r.function_name == "root")
        assert root.description == "Root endpoint."

    def test_type_hints_resolved(self):
        routes, _ = parse_django(FIXTURES / "django_simple")
        create_user = next(r for r in routes if r.function_name == "create_user")
        name_param = next(p for p in create_user.params if p.name == "name")
        assert name_param.param_type == ParamType.STRING
        age_param = next(p for p in create_user.params if p.name == "age")
        assert age_param.param_type == ParamType.INTEGER


class TestDjangoComplex:
    def test_router_viewset_routes_extracted(self):
        routes, _ = parse_django(FIXTURES / "django_complex")
        user_routes = [r for r in routes if "/users" in r.path]
        # ModelViewSet: list, create, retrieve, update, partial_update, destroy
        # + 2 @action endpoints (set_password, recent)
        assert len(user_routes) >= 8

    def test_viewset_methods_detected(self):
        routes, _ = parse_django(FIXTURES / "django_complex")
        # list = GET /api/v1/users
        user_list = next(
            r for r in routes
            if "/users" in r.path and r.method == HttpMethod.GET
            and "{" not in r.path
        )
        assert user_list.method == HttpMethod.GET

    def test_viewset_detail_route(self):
        routes, _ = parse_django(FIXTURES / "django_complex")
        user_detail = next(
            r for r in routes
            if "/users/" in r.path and r.method == HttpMethod.GET
            and "{" in r.path
        )
        assert "{pk}" in user_detail.path

    def test_action_decorator_detail(self):
        routes, _ = parse_django(FIXTURES / "django_complex")
        set_password = next(
            r for r in routes if "set-password" in r.path or "set_password" in r.path
        )
        assert set_password.method == HttpMethod.POST

    def test_action_decorator_list(self):
        routes, _ = parse_django(FIXTURES / "django_complex")
        recent = next(r for r in routes if "recent" in r.path)
        assert recent.method == HttpMethod.GET

    def test_readonly_viewset(self):
        routes, _ = parse_django(FIXTURES / "django_complex")
        post_routes = [r for r in routes if "/posts" in r.path]
        methods = {r.method for r in post_routes}
        # ReadOnlyModelViewSet: only GET (list + retrieve)
        assert methods == {HttpMethod.GET}
        assert len(post_routes) == 2

    def test_apiview_class(self):
        routes, _ = parse_django(FIXTURES / "django_complex")
        stats_routes = [r for r in routes if "/stats" in r.path]
        methods = {r.method for r in stats_routes}
        assert HttpMethod.GET in methods
        assert HttpMethod.POST in methods

    def test_include_prefix_applied(self):
        routes, _ = parse_django(FIXTURES / "django_complex")
        # Routes under include("api.urls") should have /api/v1/ prefix
        user_routes = [r for r in routes if "/users" in r.path]
        assert all("/api/v1/" in r.path for r in user_routes)

    def test_health_endpoint_found(self):
        routes, _ = parse_django(FIXTURES / "django_complex")
        health = next(r for r in routes if r.function_name == "health")
        assert health.path == "/health"
        assert health.method == HttpMethod.GET
