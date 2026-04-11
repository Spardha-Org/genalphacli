"""Publish route — builds and uploads generated packages to PyPI."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from services.core.deps import CurrentWorkspaceDep, DbDep
from services.core.models import Service
from services.core.temporal_client import get_temporal_client
from services.core.tps_client import tps

logger = logging.getLogger(__name__)
router = APIRouter(tags=["publish"])


class PublishRequest(BaseModel):
    serviceId: str
    outputTypes: list[str]  # ["cli"] or ["mcp"] or ["cli", "mcp"]
    cliName: str
    baseUrl: str


@router.post("/publish")
async def start_publish(
    body: PublishRequest,
    workspace: CurrentWorkspaceDep,
    db: DbDep,
):
    """Generate packages and publish to PyPI using user's stored API token."""

    # Validate service exists and is parsed
    result = await db.exec(select(Service).where(Service.id == body.serviceId))
    service = result.first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    if service.status not in ("parsed", "complete"):
        raise HTTPException(status_code=400, detail=f"Service must be parsed first (current: {service.status})")
    if not service.route_graph:
        raise HTTPException(status_code=400, detail="No route graph — parse the service first")

    # Look up user's PyPI integration from TPS
    pypi_integration = await tps.get_integration(workspace.owner_id, "pypi")
    if not pypi_integration:
        raise HTTPException(
            status_code=400,
            detail="No PyPI integration found. Connect your PyPI account in the App Store first.",
        )

    # Start PublishWorkflow
    workflow_id = f"publish-{service.id}"
    try:
        client = await get_temporal_client()
        await client.start_workflow(
            "PublishWorkflow",
            {
                "route_graph": service.route_graph,
                "cli_name": body.cliName,
                "base_url": body.baseUrl,
                "output_types": body.outputTypes,
                "service_id": service.id,
                "user_id": workspace.owner_id,
                "integration_id": pypi_integration["id"],
            },
            id=workflow_id,
            task_queue="genalpha-parse",
        )

        service.status = "generating"
        service.generate_workflow_id = workflow_id
        db.add(service)
        await db.commit()

        logger.info("Started PublishWorkflow %s for service %s", workflow_id, service.id)
    except Exception as e:
        logger.error("Failed to start PublishWorkflow: %s", e)
        return {
            "serviceId": service.id,
            "workflowId": workflow_id,
            "status": "failed",
            "error": str(e),
        }

    return {
        "serviceId": service.id,
        "workflowId": workflow_id,
        "status": "generating",
    }
