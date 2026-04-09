"""CLI entry point for GenAlpha CLI."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from genalphacli.config import get_github_token
from genalphacli.github import (
    cleanup_clone,
    clone_repo,
    detect_framework,
    fetch_repo_info,
    parse_github_url,
)
from genalphacli.pipeline import run_pipeline

app = typer.Typer(
    name="genalphacli",
    help="Convert API repositories into CLI tools automatically.",
    no_args_is_help=True,
)


@app.command()
def parse(
    github_url: str = typer.Argument(help="GitHub repository URL or owner/repo"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write JSON to file"),
    base_url: str | None = typer.Option(None, "--base-url", help="API base URL override"),
    auth_type: str | None = typer.Option(None, "--auth-type", help="bearer|api_key|none"),
    auth_env_var: str | None = typer.Option(None, "--auth-env-var", help="Env var for auth token"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show progress details"),
) -> None:
    """Parse a GitHub repository and generate a command graph JSON."""
    token = get_github_token()

    # Step 1: Parse URL
    try:
        owner, repo = parse_github_url(github_url)
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    if verbose:
        typer.echo(f"Parsing {owner}/{repo}...")

    # Step 2: Fetch metadata
    try:
        info = fetch_repo_info(owner, repo, token=token)
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    if verbose:
        typer.echo(f"Languages: {info.languages}")
        typer.echo(f"Size: {info.size_kb}KB")

    # Step 3: Clone
    if verbose:
        typer.echo("Cloning repository...")

    try:
        clone_dir = clone_repo(info, token=token)
    except (RuntimeError, ValueError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    try:
        # Step 4: Detect framework
        framework = detect_framework(clone_dir)
        if verbose:
            typer.echo(f"Detected framework: {framework or 'none'}")

        if not framework:
            typer.echo(
                "Warning: No supported framework detected. Will attempt OpenAPI spec parsing only.",
                err=True,
            )

        # Step 5: Run pipeline
        graph = run_pipeline(
            clone_dir,
            framework=framework,
            command_name=repo,
            user_base_url=base_url,
            user_auth_type=auth_type,
            user_auth_env_var=auth_env_var,
        )

        # Step 6: Output
        result = json.dumps(graph.model_dump(), indent=2, default=str)

        if output:
            output.write_text(result)
            typer.echo(f"Command graph written to {output}")
        else:
            typer.echo(result)

        if verbose:
            meta = graph.metadata
            typer.echo("\n--- Stats ---", err=True)
            typer.echo(f"Routes: {meta.total_routes}", err=True)
            typer.echo(f"Layers: {meta.layer_counts}", err=True)
            typer.echo(f"Files scanned: {meta.files_scanned}", err=True)
            typer.echo(f"Parse time: {meta.parse_time_ms}ms", err=True)
            if meta.warnings:
                typer.echo(f"Warnings: {len(meta.warnings)}", err=True)
                for w in meta.warnings:
                    typer.echo(f"  [{w.severity}] {w.message}", err=True)

    finally:
        cleanup_clone(clone_dir)


@app.command()
def detect(
    github_url: str = typer.Argument(help="GitHub repository URL or owner/repo"),
) -> None:
    """Detect the API framework used in a repository."""
    token = get_github_token()

    try:
        owner, repo = parse_github_url(github_url)
        info = fetch_repo_info(owner, repo, token=token)
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Repository: {info.full_name}")
    typer.echo(f"Languages: {json.dumps(info.languages)}")
    typer.echo(f"Size: {info.size_kb}KB")

    # Clone and detect
    try:
        clone_dir = clone_repo(info, token=token)
    except (RuntimeError, ValueError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    try:
        framework = detect_framework(clone_dir)
        typer.echo(f"Framework: {framework or 'unknown'}")
    finally:
        cleanup_clone(clone_dir)


@app.command(name="parse-local")
def parse_local(
    path: Path = typer.Argument(help="Local path to a repository"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write JSON to file"),
    base_url: str | None = typer.Option(None, "--base-url", help="API base URL override"),
    auth_type: str | None = typer.Option(None, "--auth-type", help="bearer|api_key|none"),
    auth_env_var: str | None = typer.Option(None, "--auth-env-var", help="Env var for auth token"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show progress details"),
) -> None:
    """Parse a local repository and generate a command graph JSON."""
    if not path.is_dir():
        typer.echo(f"Error: {path} is not a directory", err=True)
        raise typer.Exit(1)

    framework = detect_framework(path)
    if verbose:
        typer.echo(f"Detected framework: {framework or 'none'}")

    graph = run_pipeline(
        path,
        framework=framework,
        command_name=path.name,
        user_base_url=base_url,
        user_auth_type=auth_type,
        user_auth_env_var=auth_env_var,
    )
    result = json.dumps(graph.model_dump(), indent=2, default=str)

    if output:
        output.write_text(result)
        typer.echo(f"Command graph written to {output}")
    else:
        typer.echo(result)


@app.command()
def build(
    graph_file: Path = typer.Argument(help="Path to command graph JSON"),
    output_dir: Path = typer.Option("dist", "--output-dir", "-d", help="Output directory"),
    cli_name: str = typer.Option(..., "--name", "-n", help="CLI command name"),
    base_url: str = typer.Option(..., "--base-url", help="API base URL"),
    build_type: list[str] | None = typer.Option(None, "--type", help="cli|mcp (repeatable)"),
    auth_type: str | None = typer.Option(None, "--auth-type", help="bearer|api_key|none"),
    auth_env_var: str | None = typer.Option(None, "--auth-env-var", help="Env var for token"),
) -> None:
    """Generate an installable CLI and/or MCP server from a command graph JSON."""
    from genalphacli.models import AuthConfig, AuthType, BuildConfig, CommandGraph, OutputType

    # Load graph
    if not graph_file.is_file():
        typer.echo(f"Error: {graph_file} not found", err=True)
        raise typer.Exit(1)

    try:
        graph_data = json.loads(graph_file.read_text())
        graph = CommandGraph.model_validate(graph_data)
    except Exception as e:
        typer.echo(f"Error loading graph: {e}", err=True)
        raise typer.Exit(1)

    # Determine output types
    output_types: list[OutputType] = []
    if build_type:
        for t in build_type:
            try:
                output_types.append(OutputType(t))
            except ValueError:
                typer.echo(f"Error: Unknown type '{t}'. Use: cli, mcp", err=True)
                raise typer.Exit(1)
    else:
        # Interactive multi-select
        typer.echo("What would you like to generate?")
        gen_cli = typer.confirm("  CLI tool?", default=True)
        gen_mcp = typer.confirm("  MCP server?", default=True)
        if gen_cli:
            output_types.append(OutputType.CLI)
        if gen_mcp:
            output_types.append(OutputType.MCP)
        if not output_types:
            typer.echo("Error: No output type selected.", err=True)
            raise typer.Exit(1)

    # Build auth config
    at = AuthType.NONE
    if auth_type:
        try:
            at = AuthType(auth_type)
        except ValueError:
            at = graph.auth.type
    else:
        at = graph.auth.type

    env_var = auth_env_var or graph.auth.env_var or f"{cli_name.upper()}_TOKEN"

    try:
        config = BuildConfig(
            cli_name=cli_name,
            base_url=base_url,
            auth=AuthConfig(type=at, env_var=env_var),
        )
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Building from {graph_file}...")
    typer.echo(f"  Name: {cli_name}")
    typer.echo(f"  Base URL: {config.base_url}")
    typer.echo(f"  Auth: {at.value} via ${env_var}")
    typer.echo(f"  Routes: {len(graph.subcommands)}")
    typer.echo(f"  Output: {', '.join(t.value for t in output_types)}")

    # Generate CLI
    if OutputType.CLI in output_types:
        from genalphacli.generators.pip_generator import generate as gen_cli

        try:
            cli_path = gen_cli(graph, config, output_dir)
            typer.echo(f"\nCLI generated at: {cli_path}")
            typer.echo(f"  Install: cd {cli_path} && pip install .")
            typer.echo(f"  Use:     {cli_name} --help")
        except RuntimeError as e:
            typer.echo(f"Error generating CLI: {e}", err=True)
            raise typer.Exit(1)

    # Generate MCP server
    if OutputType.MCP in output_types:
        from genalphacli.generators.mcp_generator import (
            find_claude_desktop_config,
            get_claude_desktop_config,
            register_with_claude_desktop,
        )
        from genalphacli.generators.mcp_generator import (
            generate as gen_mcp,
        )

        try:
            mcp_path = gen_mcp(graph, config, output_dir)
            typer.echo(f"\nMCP server generated at: {mcp_path}")
            typer.echo(f"  Install: cd {mcp_path} && pip install .")
            typer.echo(f"  Run:     {cli_name}-mcp")
        except RuntimeError as e:
            typer.echo(f"Error generating MCP server: {e}", err=True)
            raise typer.Exit(1)

        # Print Claude Desktop config snippet
        config_snippet = get_claude_desktop_config(cli_name, config.base_url, env_var)
        typer.echo("\nClaude Desktop config:")
        typer.echo(json.dumps(config_snippet, indent=2))

        # Offer auto-register
        config_path = find_claude_desktop_config()
        if config_path and typer.confirm(f"\nAuto-register with Claude Desktop ({config_path})?"):
            if register_with_claude_desktop(config_path, cli_name, config.base_url, env_var):
                typer.echo("Registered! Restart Claude Desktop to load.")
            else:
                typer.echo("Failed to register. Add manually.", err=True)


if __name__ == "__main__":
    app()
