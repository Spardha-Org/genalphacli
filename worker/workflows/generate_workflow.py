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
        upload_artifact_activity,
    )
    from worker.activities.status_activities import update_service_status, StatusUpdateInput
    from worker.activities.schemas import (
        GeneratePackagesInput,
        PackageZipInput,
        UploadArtifactInput,
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
    artifact_id: str
    file_size: int


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
                heartbeat_timeout=timedelta(seconds=30),
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

            # Step 3: Upload artifact to Core DB
            upload_result = await workflow.execute_activity(
                upload_artifact_activity,
                UploadArtifactInput(
                    zip_path=zip_result.zip_path,
                    service_id=input.service_id,
                    artifact_type="cli",  # TODO: separate artifacts per output type
                    filename=f"{input.cli_name}.zip",
                ),
                start_to_close_timeout=timedelta(seconds=60),
                heartbeat_timeout=timedelta(seconds=20),
                retry_policy=RetryPolicy(maximum_attempts=2),
            )

            # Step 4: Update to complete
            await workflow.execute_activity(
                update_service_status,
                StatusUpdateInput(
                    service_id=input.service_id,
                    status="complete",
                    metadata={"artifact_id": upload_result.artifact_id, "file_size": upload_result.file_size},
                ),
                start_to_close_timeout=timedelta(seconds=10),
            )

            return GenerateWorkflowOutput(
                artifact_id=upload_result.artifact_id,
                file_size=upload_result.file_size,
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
