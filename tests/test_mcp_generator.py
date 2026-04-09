"""Tests for the MCP server generator."""

import ast
import json
from pathlib import Path

from genalphacli.generators.mcp_generator import (
    generate,
    get_claude_desktop_config,
    register_with_claude_desktop,
)
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
        ],
    )


def _make_config() -> BuildConfig:
    return BuildConfig(
        cli_name="testapi",
        base_url="https://api.example.com",
        auth=AuthConfig(type=AuthType.BEARER, env_var="TEST_TOKEN"),
    )


class TestMcpGenerator:
    def test_generates_package_structure(self, tmp_path):
        result = generate(_make_graph(), _make_config(), tmp_path)
        assert result.is_dir()
        assert (result / "pyproject.toml").is_file()
        assert (result / "src" / "testapi_mcp" / "server.py").is_file()
        assert (result / "src" / "testapi_mcp" / "client.py").is_file()
        assert (result / "src" / "testapi_mcp" / "__init__.py").is_file()
        assert (result / "src" / "testapi_mcp" / "_graph.json").is_file()

    def test_package_name_has_mcp_suffix(self, tmp_path):
        result = generate(_make_graph(), _make_config(), tmp_path)
        assert result.name == "testapi_mcp"

    def test_generated_server_is_valid_python(self, tmp_path):
        generate(_make_graph(), _make_config(), tmp_path)
        server = tmp_path / "testapi_mcp" / "src" / "testapi_mcp" / "server.py"
        ast.parse(server.read_text())

    def test_generated_client_is_valid_python(self, tmp_path):
        generate(_make_graph(), _make_config(), tmp_path)
        client = tmp_path / "testapi_mcp" / "src" / "testapi_mcp" / "client.py"
        ast.parse(client.read_text())

    def test_server_has_fastmcp_import(self, tmp_path):
        generate(_make_graph(), _make_config(), tmp_path)
        server = (tmp_path / "testapi_mcp" / "src" / "testapi_mcp" / "server.py").read_text()
        assert "from fastmcp import FastMCP" in server

    def test_server_has_mcp_tool_decorators(self, tmp_path):
        generate(_make_graph(), _make_config(), tmp_path)
        server = (tmp_path / "testapi_mcp" / "src" / "testapi_mcp" / "server.py").read_text()
        assert "@mcp.tool()" in server
        assert "async def list_users" in server
        assert "async def get_user" in server
        assert "async def create_user" in server

    def test_server_uses_tool_error(self, tmp_path):
        generate(_make_graph(), _make_config(), tmp_path)
        server = (tmp_path / "testapi_mcp" / "src" / "testapi_mcp" / "server.py").read_text()
        assert "from fastmcp.exceptions import ToolError" in server
        assert "raise ToolError" in server

    def test_server_has_stdio_transport(self, tmp_path):
        generate(_make_graph(), _make_config(), tmp_path)
        server = (tmp_path / "testapi_mcp" / "src" / "testapi_mcp" / "server.py").read_text()
        assert 'mcp.run(transport="stdio")' in server

    def test_server_no_print_statements(self, tmp_path):
        generate(_make_graph(), _make_config(), tmp_path)
        server = (tmp_path / "testapi_mcp" / "src" / "testapi_mcp" / "server.py").read_text()
        # No print() calls — stdio transport would be corrupted
        tree = ast.parse(server)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id != "print", "server.py must not use print()"

    def test_client_uses_httpx(self, tmp_path):
        generate(_make_graph(), _make_config(), tmp_path)
        client = (tmp_path / "testapi_mcp" / "src" / "testapi_mcp" / "client.py").read_text()
        assert "import httpx" in client
        assert "httpx.AsyncClient" in client

    def test_client_has_auth_config(self, tmp_path):
        generate(_make_graph(), _make_config(), tmp_path)
        client = (tmp_path / "testapi_mcp" / "src" / "testapi_mcp" / "client.py").read_text()
        assert 'AUTH_TYPE = "bearer"' in client
        assert 'AUTH_ENV_VAR = "TEST_TOKEN"' in client

    def test_client_has_base_url_override(self, tmp_path):
        generate(_make_graph(), _make_config(), tmp_path)
        client = (tmp_path / "testapi_mcp" / "src" / "testapi_mcp" / "client.py").read_text()
        assert "TESTAPI_BASE_URL" in client

    def test_pyproject_has_fastmcp_dep(self, tmp_path):
        generate(_make_graph(), _make_config(), tmp_path)
        pyproject = (tmp_path / "testapi_mcp" / "pyproject.toml").read_text()
        assert "fastmcp" in pyproject
        assert "httpx" in pyproject

    def test_pyproject_has_entry_point(self, tmp_path):
        generate(_make_graph(), _make_config(), tmp_path)
        pyproject = (tmp_path / "testapi_mcp" / "pyproject.toml").read_text()
        assert 'testapi-mcp = "testapi_mcp.server:main"' in pyproject

    def test_empty_graph_generates_valid_server(self, tmp_path):
        graph = CommandGraph(command="emptyapi")
        config = BuildConfig(cli_name="emptyapi", base_url="https://api.com")
        result = generate(graph, config, tmp_path)
        server = (result / "src" / "emptyapi_mcp" / "server.py").read_text()
        ast.parse(server)

    def test_from_fastapi_fixture(self, tmp_path):
        from genalphacli.pipeline import run_pipeline

        graph = run_pipeline(FIXTURES / "fastapi_simple", framework="fastapi")
        config = BuildConfig(cli_name="simpleapi", base_url="https://api.test.com")
        result = generate(graph, config, tmp_path)

        for py_file in (result / "src" / "simpleapi_mcp").glob("*.py"):
            ast.parse(py_file.read_text())

        server = (result / "src" / "simpleapi_mcp" / "server.py").read_text()
        assert "@mcp.tool()" in server


class TestClaudeDesktopConfig:
    def test_generates_config_with_uv(self, tmp_path):
        pkg_path = tmp_path / "myapi_mcp"
        pkg_path.mkdir()
        config = get_claude_desktop_config("myapi", "https://api.com", "MYAPI_TOKEN", pkg_path)
        assert "mcpServers" in config
        assert "myapi" in config["mcpServers"]
        server_config = config["mcpServers"]["myapi"]
        # Should use uv or python, not direct binary
        assert "uv" in server_config["command"] or "python" in server_config["command"]
        assert "args" in server_config
        assert "env" in server_config

    def test_config_has_env_vars(self, tmp_path):
        pkg_path = tmp_path / "myapi_mcp"
        pkg_path.mkdir()
        config = get_claude_desktop_config("myapi", "https://api.com", "MYAPI_TOKEN", pkg_path)
        env = config["mcpServers"]["myapi"]["env"]
        assert "MYAPI_TOKEN" in env
        assert "MYAPI_BASE_URL" in env

    def test_register_creates_entry(self, tmp_path):
        config_file = tmp_path / "claude_config.json"
        config_file.write_text('{"mcpServers": {}}')
        pkg_path = tmp_path / "testapi_mcp"
        pkg_path.mkdir()

        result = register_with_claude_desktop(
            config_file, "testapi", "https://api.com", "TEST_TOKEN", pkg_path
        )
        assert result is True

        data = json.loads(config_file.read_text())
        assert "testapi" in data["mcpServers"]
        # Should use uv or python
        cmd = data["mcpServers"]["testapi"]["command"]
        assert "uv" in cmd or "python" in cmd

    def test_register_preserves_existing(self, tmp_path):
        config_file = tmp_path / "claude_config.json"
        config_file.write_text('{"mcpServers": {"existing": {"command": "existing-mcp"}}}')
        pkg_path = tmp_path / "newapi_mcp"
        pkg_path.mkdir()

        register_with_claude_desktop(config_file, "newapi", "https://api.com", "TOKEN", pkg_path)

        data = json.loads(config_file.read_text())
        assert "existing" in data["mcpServers"]
        assert "newapi" in data["mcpServers"]
