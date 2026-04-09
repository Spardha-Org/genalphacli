"""Tests for the CLI generator."""

import ast
import json
from pathlib import Path

import pytest

from genalphacli.generators.pip_generator import generate
from genalphacli.models import (
    AuthConfig,
    AuthType,
    BuildConfig,
    CommandGraph,
    CommandParam,
    HttpMethod,
    ParamType,
    Subcommand,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _make_graph() -> CommandGraph:
    """Create a test CommandGraph with various route types."""
    return CommandGraph(
        command="testapi",
        base_url="https://api.example.com",
        auth=AuthConfig(type=AuthType.BEARER, env_var="TEST_TOKEN"),
        subcommands=[
            Subcommand(
                name="list-users",
                description="List all users.",
                method=HttpMethod.GET,
                endpoint="/users",
                params=[
                    CommandParam(
                        name="limit", flag="--limit", type=ParamType.INTEGER, required=False
                    ),
                    CommandParam(
                        name="offset", flag="--offset", type=ParamType.INTEGER, required=False
                    ),
                ],
            ),
            Subcommand(
                name="get-user",
                description="Get a user by ID.",
                method=HttpMethod.GET,
                endpoint="/users/{user_id}",
                params=[
                    CommandParam(
                        name="user_id", flag="--user-id", type=ParamType.STRING, required=True
                    ),
                ],
            ),
            Subcommand(
                name="create-user",
                description="Create a new user.",
                method=HttpMethod.POST,
                endpoint="/users",
                params=[
                    CommandParam(name="name", flag="--name", type=ParamType.STRING, required=True),
                    CommandParam(
                        name="email", flag="--email", type=ParamType.STRING, required=True
                    ),
                ],
            ),
            Subcommand(
                name="delete-user",
                description="Delete a user.",
                method=HttpMethod.DELETE,
                endpoint="/users/{user_id}",
                params=[
                    CommandParam(
                        name="user_id", flag="--user-id", type=ParamType.STRING, required=True
                    ),
                ],
            ),
        ],
    )


def _make_config() -> BuildConfig:
    return BuildConfig(
        cli_name="testapi",
        base_url="https://api.example.com",
        auth=AuthConfig(type=AuthType.BEARER, env_var="TEST_TOKEN"),
    )


class TestBuildConfig:
    def test_valid_config(self):
        config = BuildConfig(cli_name="myapi", base_url="https://api.example.com")
        assert config.cli_name == "myapi"
        assert config.base_url == "https://api.example.com"

    def test_rejects_invalid_cli_name(self):
        with pytest.raises(Exception, match="valid Python identifier"):
            BuildConfig(cli_name="My-API", base_url="https://api.com")

    def test_rejects_cli_name_starting_with_digit(self):
        with pytest.raises(Exception, match="valid Python identifier"):
            BuildConfig(cli_name="123api", base_url="https://api.com")

    def test_rejects_private_ip(self):
        with pytest.raises(Exception, match="private"):
            BuildConfig(cli_name="myapi", base_url="http://192.168.1.1/api")

    def test_rejects_loopback(self):
        with pytest.raises(Exception, match="private|loopback"):
            BuildConfig(cli_name="myapi", base_url="http://127.0.0.1/api")

    def test_strips_trailing_slash(self):
        config = BuildConfig(cli_name="myapi", base_url="https://api.example.com/")
        assert config.base_url == "https://api.example.com"

    def test_allows_http_for_domains(self):
        config = BuildConfig(cli_name="myapi", base_url="http://api.example.com")
        assert config.base_url == "http://api.example.com"


class TestPipGenerator:
    def test_generates_package_structure(self, tmp_path):
        graph = _make_graph()
        config = _make_config()
        result = generate(graph, config, tmp_path)

        assert result.is_dir()
        assert (result / "pyproject.toml").is_file()
        assert (result / "src" / "testapi" / "cli.py").is_file()
        assert (result / "src" / "testapi" / "client.py").is_file()
        assert (result / "src" / "testapi" / "__init__.py").is_file()
        assert (result / "src" / "testapi" / "_graph.json").is_file()

    def test_generated_cli_is_valid_python(self, tmp_path):
        graph = _make_graph()
        config = _make_config()
        generate(graph, config, tmp_path)

        cli_path = tmp_path / "testapi" / "src" / "testapi" / "cli.py"
        ast.parse(cli_path.read_text())

    def test_generated_client_is_valid_python(self, tmp_path):
        graph = _make_graph()
        config = _make_config()
        generate(graph, config, tmp_path)

        client_path = tmp_path / "testapi" / "src" / "testapi" / "client.py"
        ast.parse(client_path.read_text())

    def test_generated_pyproject_has_entry_point(self, tmp_path):
        graph = _make_graph()
        config = _make_config()
        generate(graph, config, tmp_path)

        pyproject = (tmp_path / "testapi" / "pyproject.toml").read_text()
        assert 'testapi = "testapi.cli:app"' in pyproject

    def test_generated_client_has_correct_base_url(self, tmp_path):
        graph = _make_graph()
        config = _make_config()
        generate(graph, config, tmp_path)

        client = (tmp_path / "testapi" / "src" / "testapi" / "client.py").read_text()
        assert "https://api.example.com" in client
        assert "TESTAPI_BASE_URL" in client  # env override

    def test_generated_client_has_auth_config(self, tmp_path):
        graph = _make_graph()
        config = _make_config()
        generate(graph, config, tmp_path)

        client = (tmp_path / "testapi" / "src" / "testapi" / "client.py").read_text()
        assert 'AUTH_TYPE = "bearer"' in client
        assert 'AUTH_ENV_VAR = "TEST_TOKEN"' in client

    def test_generated_cli_has_all_commands(self, tmp_path):
        graph = _make_graph()
        config = _make_config()
        generate(graph, config, tmp_path)

        cli = (tmp_path / "testapi" / "src" / "testapi" / "cli.py").read_text()
        assert "list-users" in cli
        assert "get-user" in cli
        assert "create-user" in cli
        assert "delete-user" in cli

    def test_path_params_are_positional(self, tmp_path):
        graph = _make_graph()
        config = _make_config()
        generate(graph, config, tmp_path)

        cli = (tmp_path / "testapi" / "src" / "testapi" / "cli.py").read_text()
        assert "typer.Argument" in cli  # path params use Argument

    def test_body_params_have_body_override(self, tmp_path):
        graph = _make_graph()
        config = _make_config()
        generate(graph, config, tmp_path)

        cli = (tmp_path / "testapi" / "src" / "testapi" / "cli.py").read_text()
        assert '"--body"' in cli  # raw JSON override

    def test_generated_graph_json_embedded(self, tmp_path):
        graph = _make_graph()
        config = _make_config()
        generate(graph, config, tmp_path)

        graph_path = tmp_path / "testapi" / "src" / "testapi" / "_graph.json"
        data = json.loads(graph_path.read_text())
        assert data["command"] == "testapi"
        assert len(data["subcommands"]) == 4

    def test_empty_graph_generates_empty_cli(self, tmp_path):
        graph = CommandGraph(command="emptyapi")
        config = BuildConfig(cli_name="emptyapi", base_url="https://api.com")
        result = generate(graph, config, tmp_path)

        cli = (result / "src" / "emptyapi" / "cli.py").read_text()
        ast.parse(cli)  # should still be valid Python


class TestGeneratedCodeFromRealGraph:
    """Test generation from a real parsed graph."""

    def test_from_fastapi_fixture(self, tmp_path):
        from genalphacli.pipeline import run_pipeline

        graph = run_pipeline(FIXTURES / "fastapi_simple", framework="fastapi")
        config = BuildConfig(cli_name="simpleapi", base_url="https://api.test.com")
        result = generate(graph, config, tmp_path)

        # All generated files should be valid Python
        for py_file in (result / "src" / "simpleapi").glob("*.py"):
            ast.parse(py_file.read_text())

        # Should have commands for all 5 routes
        cli = (result / "src" / "simpleapi" / "cli.py").read_text()
        assert "list-users" in cli
        assert "get-user" in cli
        assert "create-user" in cli
