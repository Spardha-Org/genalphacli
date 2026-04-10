"""GenerateWorkflow — Generate CLI/MCP packages and create downloadable zip.

Updates Core DB status after each step via status_activities.
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
    from worker.activities.status_activities import update_service_status, StatusUpdateInput
    from worker.activities.schemas import (
        GeneratePackagesInput,
        PackageZipInput,
    )


@dataclass
class GenerateWorkflowInput:
    route_graph: dict
    cli_name: str
    base_url: str
    output_types: list[str]
    service_id: str


@dataclass
class GenerateWorkflowOutput:
    zip_path: str
    zip_size_bytes: int


@workflow.defn
class GenerateWorkflow:

    @workflow.run
    async def run(self, input: GenerateWorkflowInput) -> GenerateWorkflowOutput:
        try:
            # Step 1: Generate packages
            await workflow.execute_activity(
                update_service_status,
                StatusUpdateInput(service_id=input.service_id, status="generating"),
                start_to_close_timeout=timedelta(seconds=10),
            )

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
            await workflow.execute_activity(
                update_service_status,
                StatusUpdateInput(service_id=input.service_id, status="packaging"),
                start_to_close_timeout=timedelta(seconds=10),
            )

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

            # Step 3: Update to complete with download URL
            await workflow.execute_activity(
                update_service_status,
                StatusUpdateInput(
                    service_id=input.service_id,
                    status="complete",
                    metadata={"zip_path": zip_result.zip_path, "zip_size_bytes": zip_result.zip_size_bytes},
                ),
                start_to_close_timeout=timedelta(seconds=10),
            )

            return GenerateWorkflowOutput(
                zip_path=zip_result.zip_path,
                zip_size_bytes=zip_result.zip_size_bytes,
            )

        except Exception as e:
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
            raise
