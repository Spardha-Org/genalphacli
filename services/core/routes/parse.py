"""Parse route — validates input, creates service, starts Temporal workflow."""

from __future__ import annotations

import re
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select, func

from services.core.deps import CurrentWorkspaceDep, DbDep
from services.core.models import Project, Service

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

    # Validate GitHub URL (SSRF prevention)
    match = GITHUB_URL_RE.match(body.repoUrl.strip())
    if not match:
        raise HTTPException(
            status_code=400,
            detail="Invalid GitHub URL. Format: https://github.com/owner/repo",
        )

    owner, repo = match.group(1), match.group(2)

    # Validate project belongs to workspace
    project = await db.exec(
        select(Project).where(
            Project.id == body.projectId,
            Project.workspace_id == workspace.id,
        )
    )
    project = project.first()
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

    # TODO: Start Temporal ParseWorkflow here
    # For now, just set status to "parsed" with a placeholder
    # This will be wired to Temporal when the worker integration is complete
    logger.info("Parse requested for %s/%s (service %s)", owner, repo, service.id)

    return {
        "serviceId": service.id,
        "workflowId": f"parse-{service.id}",
        "status": "cloning",
    }
