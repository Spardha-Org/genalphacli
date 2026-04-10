"""ParseWorkflow — Clone, detect framework, parse routes.

This is the first of two workflows in the pipeline.
After completion, the user reviews the mindmap and triggers GenerateWorkflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from worker.activities.github_activities import (
        cleanup_clone_activity,
        clone_repo_activity,
    )
    from worker.activities.parse_activities import parse_routes_activity
    from worker.activities.schemas import (
        CloneRepoInput,
        ParseRoutesInput,
    )


@dataclass
class ParseWorkflowInput:
    """Input for ParseWorkflow."""

    owner: str
    repo: str
    user_id: str
    service_id: str
    command_name: str


@dataclass
class ParseWorkflowOutput:
    """Output from ParseWorkflow."""

    route_graph: dict
    route_count: int
    parse_time_ms: int
    framework: str | None
    warnings: list[str]


@workflow.defn
class ParseWorkflow:
    """Parse a GitHub repo's API routes.

    Steps:
    1. Clone the repo (with retry for network issues)
    2. Parse API routes using the genalphacli pipeline
    3. Clean up the clone directory
    4. Return the parsed graph

    Status is tracked via workflow query for frontend progress display.
    """

    def __init__(self) -> None:
        self._status = "initialized"
        self._step = 0
        self._total_steps = 3
        self._error: str | None = None
        self._clone_dir: str | None = None

    @workflow.run
    async def run(self, input: ParseWorkflowInput) -> ParseWorkflowOutput:
        try:
            # Step 1: Clone repo
            self._status = "cloning"
            self._step = 1

            clone_result = await workflow.execute_activity(
                clone_repo_activity,
                CloneRepoInput(
                    owner=input.owner,
                    repo=input.repo,
                    user_id=input.user_id,
                    service_id=input.service_id,
                ),
                start_to_close_timeout=timedelta(seconds=120),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=2),
                    backoff_coefficient=2.0,
                    maximum_attempts=3,
                ),
            )
            self._clone_dir = clone_result.clone_dir

            # Step 2: Parse routes
            self._status = "parsing"
            self._step = 2

            parse_result = await workflow.execute_activity(
                parse_routes_activity,
                ParseRoutesInput(
                    clone_dir=clone_result.clone_dir,
                    framework=clone_result.framework,
                    command_name=input.command_name,
                ),
                start_to_close_timeout=timedelta(seconds=180),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )

            # Step 3: Cleanup
            self._status = "cleaning_up"
            self._step = 3

            await workflow.execute_activity(
                cleanup_clone_activity,
                clone_result.clone_dir,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )

            self._status = "completed"
            return ParseWorkflowOutput(
                route_graph=parse_result.route_graph,
                route_count=parse_result.route_count,
                parse_time_ms=parse_result.parse_time_ms,
                framework=clone_result.framework,
                warnings=parse_result.warnings,
            )

        except Exception as e:
            self._status = "failed"
            self._error = str(e)

            # Best-effort cleanup on failure
            if self._clone_dir:
                try:
                    await workflow.execute_activity(
                        cleanup_clone_activity,
                        self._clone_dir,
                        start_to_close_timeout=timedelta(seconds=30),
                        retry_policy=RetryPolicy(maximum_attempts=1),
                    )
                except Exception:
                    pass  # Cleanup failure is non-fatal

            raise

    @workflow.query
    def get_status(self) -> dict:
        """Query current workflow status for frontend progress display."""
        return {
            "status": self._status,
            "step": self._step,
            "total_steps": self._total_steps,
            "error": self._error,
        }
