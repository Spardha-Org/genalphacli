"""Generate route — starts generation workflow for a parsed service."""

from __future__ import annotations

import logging
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from services.core.deps import CurrentWorkspaceDep, DbDep
from services.core.models import Project, Service
from services.core.temporal_client import get_temporal_client

logger = logging.getLogger(__name__)
router = APIRouter(tags=["generate"])


class GenerateRequest(BaseModel):
    serviceId: str
    outputTypes: list[str]
    cliName: str
    baseUrl: str


@router.post("/generate")
async def start_generate(
    body: GenerateRequest,
    workspace: CurrentWorkspaceDep,
    db: DbDep,
):
    """Start generation workflow for a parsed service."""

    if not re.match(r"^[a-z][a-z0-9_]*$", body.cliName):
        raise HTTPException(
            status_code=400,
            detail="CLI name must start with a letter and contain only lowercase letters, numbers, and underscores",
        )

    result = await db.exec(
        select(Service)
        .join(Project)
        .where(Service.id == body.serviceId, Project.workspace_id == workspace.id)
    )
    service = result.first()

    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    if service.status not in ("parsed", "complete"):
        raise HTTPException(status_code=400, detail=f"Cannot generate from status: {service.status}")

    if not service.route_graph:
        raise HTTPException(status_code=400, detail="No route graph available")

    workflow_id = f"generate-{service.id}"

    try:
        service.status = "generating"
        service.generate_workflow_id = workflow_id
        db.add(service)
        await db.commit()

        client = await get_temporal_client()
        await client.start_workflow(
            "GenerateWorkflow",
            {
                "route_graph": service.route_graph,
                "cli_name": body.cliName,
                "base_url": body.baseUrl,
                "output_types": body.outputTypes,
                "service_id": service.id,
            },
            id=workflow_id,
            task_queue="genalpha-parse",  # Same queue as parse (single worker)
        )

        logger.info("Started GenerateWorkflow %s for service %s", workflow_id, service.id)
    except Exception as e:
        logger.error("Failed to start GenerateWorkflow: %s", e)
        service.status = "failed"
        service.error_message = f"Failed to start generation: {e}"
        db.add(service)
        await db.commit()

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
