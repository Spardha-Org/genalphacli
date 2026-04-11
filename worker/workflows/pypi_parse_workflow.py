"""PyPIParseWorkflow — Fetch sdist, detect framework, parse routes.

Updates Core DB status after each step via status_activities.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from worker.activities.github_activities import cleanup_clone_activity
    from worker.activities.parse_activities import parse_routes_activity
    from worker.activities.pypi_activities import fetch_pypi_sdist_activity
    from worker.activities.schemas import (
        FetchPyPISdistInput,
        ParseRoutesInput,
    )
    from worker.activities.status_activities import (
        StatusUpdateInput,
        update_service_status,
    )
    from worker.workflows.parse_workflow import ParseWorkflowOutput


@dataclass
class PyPIParseWorkflowInput:
    package_name: str
    user_id: str
    service_id: str
    command_name: str
    workspace_id: str = ""
    version: str | None = None


@workflow.defn
class PyPIParseWorkflow:

    @workflow.run
    async def run(self, input: PyPIParseWorkflowInput) -> ParseWorkflowOutput:
        extract_dir: str | None = None

        try:
            # Step 1: Fetch and extract sdist
            await workflow.execute_activity(
                update_service_status,
                StatusUpdateInput(service_id=input.service_id, status="downloading"),
                start_to_close_timeout=timedelta(seconds=10),
            )

            fetch_result = await workflow.execute_activity(
                fetch_pypi_sdist_activity,
                FetchPyPISdistInput(
                    package_name=input.package_name,
                    version=input.version,
                    service_id=input.service_id,
                    user_id=input.user_id,
                ),
                start_to_close_timeout=timedelta(seconds=120),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=2),
                    backoff_coefficient=2.0,
                    maximum_attempts=3,
                ),
            )
            extract_dir = fetch_result.extract_dir

            # Step 2: Parse routes (reuse existing activity)
            await workflow.execute_activity(
                update_service_status,
                StatusUpdateInput(
                    service_id=input.service_id,
                    status="parsing",
                    framework=fetch_result.framework,
                ),
                start_to_close_timeout=timedelta(seconds=10),
            )

            parse_result = await workflow.execute_activity(
                parse_routes_activity,
                ParseRoutesInput(
                    clone_dir=fetch_result.extract_dir,
                    framework=fetch_result.framework,
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
                        "source_type": "pypi",
                        "package_version": fetch_result.package_version,
                        "package_summary": fetch_result.package_summary,
                        "total_routes": parse_result.route_count,
                        "parse_time_ms": parse_result.parse_time_ms,
                        "warnings": parse_result.warnings,
                    },
                ),
                start_to_close_timeout=timedelta(seconds=10),
            )

            # Cleanup extracted directory
            if extract_dir:
                await workflow.execute_activity(
                    cleanup_clone_activity,
                    extract_dir,
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=RetryPolicy(maximum_attempts=1),
                )

            return ParseWorkflowOutput(
                route_graph=parse_result.route_graph,
                route_count=parse_result.route_count,
                parse_time_ms=parse_result.parse_time_ms,
                framework=fetch_result.framework,
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
            if extract_dir:
                try:
                    await workflow.execute_activity(
                        cleanup_clone_activity,
                        extract_dir,
                        start_to_close_timeout=timedelta(seconds=30),
                        retry_policy=RetryPolicy(maximum_attempts=1),
                    )
                except Exception:
                    pass

            raise
