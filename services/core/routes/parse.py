"""Parse route — validates input, creates service, starts Temporal workflow."""

from __future__ import annotations

import re
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select, func

from services.core.deps import CurrentWorkspaceDep, DbDep
from services.core.models import Project, Service
from services.core.temporal_client import get_temporal_client

logger = logging.getLogger(__name__)
router = APIRouter(tags=["parse"])

GITHUB_URL_RE = re.compile(r"^https://github\.com/([a-zA-Z0-9._-]+)/([a-zA-Z0-9._-]+?)(?:\.git)?/?$")
MAX_SERVICES_PER_WORKSPACE = 2
ACTIVE_STATUSES = ["parsed", "generating", "packaging", "complete"]


class ParseRequest(BaseModel):
    repoUrl: str
    projectId: str


@router.post("/parse")
async def start_parse(
    body: ParseRequest,
    workspace: CurrentWorkspaceDep,
    db: DbDep,
):
    """Validate GitHub URL, check limits, create service record, start parse workflow."""

    # Validate GitHub URL
    match = GITHUB_URL_RE.match(body.repoUrl.strip())
    if not match:
        raise HTTPException(
            status_code=400,
            detail="Invalid GitHub URL. Format: https://github.com/owner/repo",
        )

    owner, repo = match.group(1), match.group(2)

    # Validate project belongs to workspace
    project_result = await db.exec(
        select(Project).where(
            Project.id == body.projectId,
            Project.workspace_id == workspace.id,
        )
    )
    project = project_result.first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check service limit
    active_count_result = await db.exec(
        select(func.count())
        .select_from(Service)
        .join(Project)
        .where(
            Project.workspace_id == workspace.id,
            Service.status.in_(ACTIVE_STATUSES),
        )
    )
    active_count = active_count_result.first() or 0

    if active_count >= MAX_SERVICES_PER_WORKSPACE:
        raise HTTPException(
            status_code=429,
            detail="Service limit reached (2 per workspace). Delete a service to free up a slot.",
        )

    # Create service record
    service = Service(
        project_id=body.projectId,
        name=repo,
        repo_url=body.repoUrl.strip(),
        status="cloning",
    )
    db.add(service)
    await db.commit()
    await db.refresh(service)

    # Start Temporal ParseWorkflow
    workflow_id = f"parse-{service.id}"
    try:
        client = await get_temporal_client()
        await client.start_workflow(
            "ParseWorkflow",
            {
                "owner": owner,
                "repo": repo,
                "user_id": workspace.owner_id,
                "service_id": service.id,
                "command_name": repo,
            },
            id=workflow_id,
            task_queue="genalpha-parse",
        )

        service.parse_workflow_id = workflow_id
        db.add(service)
        await db.commit()

        logger.info("Started ParseWorkflow %s for %s/%s", workflow_id, owner, repo)
    except Exception as e:
        logger.error("Failed to start ParseWorkflow: %s", e)
        service.status = "failed"
        service.error_message = f"Failed to start parse: {e}"
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
        "status": "cloning",
    }


class StatusUpdateRequest(BaseModel):
    """Called by the Temporal worker to update service status in Core DB."""
    status: str
    error_message: str | None = None
    framework: str | None = None
    route_graph: dict | None = None
    metadata: dict | None = None


@router.post("/services/{service_id}/status")
async def update_service_status(
    service_id: str,
    body: StatusUpdateRequest,
    db: DbDep,
):
    """Update service status — called by Temporal worker activities."""
    result = await db.exec(select(Service).where(Service.id == service_id))
    service = result.first()

    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    service.status = body.status
    if body.error_message is not None:
        service.error_message = body.error_message
    if body.framework is not None:
        service.framework = body.framework
    if body.route_graph is not None:
        service.route_graph = body.route_graph
    if body.metadata is not None:
        service.metadata_json = body.metadata

    db.add(service)
    await db.commit()

    logger.info("Service %s status updated to %s", service_id, body.status)
    return {"ok": True}
