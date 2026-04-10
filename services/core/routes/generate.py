"""Generate route — starts generation workflow for a parsed service."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from services.core.deps import CurrentWorkspaceDep, DbDep
from services.core.models import Project, Service

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

    # Validate CLI name
    import re
    if not re.match(r"^[a-z][a-z0-9_]*$", body.cliName):
        raise HTTPException(
            status_code=400,
            detail="CLI name must start with a letter and contain only lowercase letters, numbers, and underscores",
        )

    # Get service with ownership check
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

    # Update status
    service.status = "generating"
    service.generate_workflow_id = f"generate-{service.id}"
    db.add(service)
    await db.commit()

    # TODO: Start Temporal GenerateWorkflow here
    logger.info("Generate requested for service %s (cli: %s)", service.id, body.cliName)

    return {
        "serviceId": service.id,
        "workflowId": f"generate-{service.id}",
        "status": "generating",
    }
