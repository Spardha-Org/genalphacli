"""Generate and publish service — workflow orchestration."""

from __future__ import annotations

import logging

from sqlmodel.ext.asyncio.session import AsyncSession

from services.core.clients.temporal_client import TemporalClient
from services.core.clients.tps_client import TpsHttpClient
from services.core.exceptions import NotFoundError, ValidationError
from services.core.models import Workspace
from services.core.repositories.service_repo import ServiceRepository

logger = logging.getLogger(__name__)


class GenerateResult:
    def __init__(self, service_id: str, workflow_id: str, status: str):
        self.service_id = service_id
        self.workflow_id = workflow_id
        self.status = status


class GenerateService:
    def __init__(
        self,
        db: AsyncSession,
        services: ServiceRepository,
        tps: TpsHttpClient,
        temporal: TemporalClient,
    ):
        self._db = db
        self._services = services
        self._tps = tps
        self._temporal = temporal

    async def start_generate(
        self,
        service_id: str,
        output_types: list[str],
        cli_name: str,
        base_url: str,
        workspace: Workspace,
    ) -> GenerateResult:
        """Generate CLI/MCP packages for a parsed service."""
        service = await self._services.find_by_id_with_ownership(service_id, workspace.id)
        if not service:
            raise NotFoundError("Service not found")
        if service.status not in ("parsed", "complete"):
            raise ValidationError(f"Service must be parsed first (current: {service.status})")
        if not service.route_graph:
            raise ValidationError("No route graph — parse the service first")

        await self._services.update(service, status="generating")

        workflow_id = await self._temporal.start_workflow(
            "GenerateWorkflow",
            {
                "route_graph": service.route_graph,
                "cli_name": cli_name,
                "base_url": base_url,
                "output_types": output_types,
                "service_id": service.id,
            },
            service_id=service.id,
            prefix="generate",
        )

        await self._services.update(service, generate_workflow_id=workflow_id)
        await self._db.commit()

        return GenerateResult(service_id=service.id, workflow_id=workflow_id, status="generating")

    async def start_publish(
        self,
        service_id: str,
        output_types: list[str],
        cli_name: str,
        base_url: str,
        workspace: Workspace,
    ) -> GenerateResult:
        """Generate + publish packages to PyPI."""
        service = await self._services.find_by_id_with_ownership(service_id, workspace.id)
        if not service:
            raise NotFoundError("Service not found")
        if service.status not in ("parsed", "complete"):
            raise ValidationError(f"Service must be parsed first (current: {service.status})")
        if not service.route_graph:
            raise ValidationError("No route graph — parse the service first")

        # Look up PyPI integration
        pypi = await self._tps.get_integration(workspace.owner_id, "pypi")
        if not pypi:
            raise ValidationError("No PyPI integration. Connect your PyPI account in the App Store.")

        await self._services.update(service, status="generating")

        workflow_id = await self._temporal.start_workflow(
            "PublishWorkflow",
            {
                "route_graph": service.route_graph,
                "cli_name": cli_name,
                "base_url": base_url,
                "output_types": output_types,
                "service_id": service.id,
                "user_id": workspace.owner_id,
                "integration_id": pypi["id"],
            },
            service_id=service.id,
            prefix="publish",
        )

        await self._services.update(service, generate_workflow_id=workflow_id)
        await self._db.commit()

        return GenerateResult(service_id=service.id, workflow_id=workflow_id, status="generating")
