"""GenerateWorkflow — Generate CLI/MCP packages and create downloadable zip.

This is the second workflow, triggered after the user reviews the mindmap.
The workflow returns the zip path — the Next.js layer owns the DB update.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from worker.activities.generate_activities import (
        generate_packages_activity,
        package_zip_activity,
    )
    from worker.activities.schemas import (
        GeneratePackagesInput,
        PackageZipInput,
    )


@dataclass
class GenerateWorkflowInput:
    """Input for GenerateWorkflow."""

    route_graph: dict
    cli_name: str
    base_url: str
    output_types: list[str]  # ["cli", "mcp"]
    service_id: str


@dataclass
class GenerateWorkflowOutput:
    """Output from GenerateWorkflow."""

    zip_path: str
    zip_size_bytes: int


@workflow.defn
class GenerateWorkflow:
    """Generate CLI/MCP packages from a parsed route graph.

    Steps:
    1. Generate packages (CLI and/or MCP)
    2. Package into a zip file
    3. Return zip path for the Next.js layer to serve

    The Next.js layer updates the service record — this workflow does NOT write to the DB.
    """

    def __init__(self) -> None:
        self._status = "initialized"
        self._step = 0
        self._total_steps = 2
        self._error: str | None = None

    @workflow.run
    async def run(self, input: GenerateWorkflowInput) -> GenerateWorkflowOutput:
        try:
            # Step 1: Generate packages
            self._status = "generating"
            self._step = 1

            gen_result = await workflow.execute_activity(
                generate_packages_activity,
                GeneratePackagesInput(
                    route_graph=input.route_graph,
                    cli_name=input.cli_name,
                    base_url=input.base_url,
                    output_types=input.output_types,
                    service_id=input.service_id,
                ),
                start_to_close_timeout=timedelta(seconds=120),
                retry_policy=RetryPolicy(maximum_attempts=2),
            )

            # Step 2: Package as zip
            self._status = "packaging"
            self._step = 2

            zip_result = await workflow.execute_activity(
                package_zip_activity,
                PackageZipInput(
                    output_dir=gen_result.output_dir,
                    cli_name=input.cli_name,
                    service_id=input.service_id,
                ),
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )

            self._status = "completed"
            return GenerateWorkflowOutput(
                zip_path=zip_result.zip_path,
                zip_size_bytes=zip_result.zip_size_bytes,
            )

        except Exception as e:
            self._status = "failed"
            self._error = str(e)
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
