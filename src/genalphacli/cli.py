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
        graph = run_pipeline(clone_dir, framework=framework, command_name=repo)

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
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show progress details"),
) -> None:
    """Parse a local repository and generate a command graph JSON."""
    if not path.is_dir():
        typer.echo(f"Error: {path} is not a directory", err=True)
        raise typer.Exit(1)

    framework = detect_framework(path)
    if verbose:
        typer.echo(f"Detected framework: {framework or 'none'}")

    graph = run_pipeline(path, framework=framework, command_name=path.name)
    result = json.dumps(graph.model_dump(), indent=2, default=str)

    if output:
        output.write_text(result)
        typer.echo(f"Command graph written to {output}")
    else:
        typer.echo(result)


if __name__ == "__main__":
    app()
