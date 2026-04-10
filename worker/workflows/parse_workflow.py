"""ParseWorkflow — Clone, detect framework, parse routes.

Updates Core DB status after each step via status_activities.
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
    from worker.activities.status_activities import update_service_status
    from worker.activities.schemas import (
        CloneRepoInput,
        ParseRoutesInput,
    )
    from worker.activities.status_activities import StatusUpdateInput


@dataclass
class ParseWorkflowInput:
    owner: str
    repo: str
    user_id: str
    service_id: str
    command_name: str


@dataclass
class ParseWorkflowOutput:
    route_graph: dict
    route_count: int
    parse_time_ms: int
    framework: str | None
    warnings: list[str]


@workflow.defn
class ParseWorkflow:

    @workflow.run
    async def run(self, input: ParseWorkflowInput) -> ParseWorkflowOutput:
        clone_dir: str | None = None

        try:
            # Step 1: Clone repo
            await workflow.execute_activity(
                update_service_status,
                StatusUpdateInput(service_id=input.service_id, status="cloning"),
                start_to_close_timeout=timedelta(seconds=10),
            )

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
            clone_dir = clone_result.clone_dir

            # Step 2: Parse routes
            await workflow.execute_activity(
                update_service_status,
                StatusUpdateInput(
                    service_id=input.service_id,
                    status="parsing",
                    framework=clone_result.framework,
                ),
                start_to_close_timeout=timedelta(seconds=10),
            )

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

            # Step 3: Update status to parsed with route graph
            await workflow.execute_activity(
                update_service_status,
                StatusUpdateInput(
                    service_id=input.service_id,
                    status="parsed",
                    route_graph=parse_result.route_graph,
                    metadata={
                        "total_routes": parse_result.route_count,
                        "parse_time_ms": parse_result.parse_time_ms,
                        "warnings": parse_result.warnings,
                    },
                ),
                start_to_close_timeout=timedelta(seconds=10),
            )

            # Cleanup clone directory
            if clone_dir:
                await workflow.execute_activity(
                    cleanup_clone_activity,
                    clone_dir,
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=RetryPolicy(maximum_attempts=1),
                )

            return ParseWorkflowOutput(
                route_graph=parse_result.route_graph,
                route_count=parse_result.route_count,
                parse_time_ms=parse_result.parse_time_ms,
                framework=clone_result.framework,
                warnings=parse_result.warnings,
            )

        except Exception as e:
            # Update status to failed
            try:
                await workflow.execute_activity(
                    update_service_status,
                    StatusUpdateInput(
                        service_id=input.service_id,
                        status="failed",
                        error_message=str(e),
                    ),
                    start_to_close_timeout=timedelta(seconds=10),
                )
            except Exception:
                pass

            # Cleanup on failure
            if clone_dir:
                try:
                    await workflow.execute_activity(
                        cleanup_clone_activity,
                        clone_dir,
                        start_to_close_timeout=timedelta(seconds=30),
                        retry_policy=RetryPolicy(maximum_attempts=1),
                    )
                except Exception:
                    pass

            raise
