"""PublishWorkflow — Generate packages and publish to PyPI.

Extends the generate flow with a PyPI publish step.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from worker.activities.generate_activities import (
        generate_packages_activity,
    )
    from worker.activities.publish_activities import publish_to_pypi_activity
    from worker.activities.status_activities import update_service_status, StatusUpdateInput
    from worker.activities.schemas import (
        GeneratePackagesInput,
        PublishToPyPIInput,
    )


@dataclass
class PublishWorkflowInput:
    route_graph: dict
    cli_name: str
    base_url: str
    output_types: list[str]  # ["cli", "mcp"]
    service_id: str
    user_id: str
    integration_id: str  # PyPI TPS integration ID


@dataclass
class PublishWorkflowOutput:
    package_name: str
    version: str
    published_url: str


@workflow.defn
class PublishWorkflow:

    @workflow.run
    async def run(self, input: PublishWorkflowInput) -> PublishWorkflowOutput:
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

            # Step 2: Build and publish to PyPI
            await workflow.execute_activity(
                update_service_status,
                StatusUpdateInput(service_id=input.service_id, status="publishing"),
                start_to_close_timeout=timedelta(seconds=10),
            )

            # Publish each output type
            publish_result = None
            for pkg_type in input.output_types:
                publish_result = await workflow.execute_activity(
                    publish_to_pypi_activity,
                    PublishToPyPIInput(
                        service_id=input.service_id,
                        user_id=input.user_id,
                        output_dir=gen_result.output_dir,
                        package_type=pkg_type,
                        integration_id=input.integration_id,
                    ),
                    start_to_close_timeout=timedelta(seconds=180),
                    retry_policy=RetryPolicy(maximum_attempts=2),
                )

            # Step 3: Mark complete
            await workflow.execute_activity(
                update_service_status,
                StatusUpdateInput(
                    service_id=input.service_id,
                    status="complete",
                    metadata={
                        "published_to_pypi": True,
                        "package_name": publish_result.package_name,
                        "package_version": publish_result.version,
                        "pypi_url": publish_result.published_url,
                    },
                ),
                start_to_close_timeout=timedelta(seconds=10),
            )

            return PublishWorkflowOutput(
                package_name=publish_result.package_name,
                version=publish_result.version,
                published_url=publish_result.published_url,
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
