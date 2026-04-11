"""PyPI parse route — validates input, creates service, starts Temporal workflow."""

from __future__ import annotations

import re
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from services.core.deps import CurrentWorkspaceDep, DbDep
from services.core.models import Project, Service
from services.core.temporal_client import get_temporal_client

logger = logging.getLogger(__name__)
router = APIRouter(tags=["parse"])

PYPI_PACKAGE_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?$")


class PyPIParseRequest(BaseModel):
    packageName: str
    projectId: str
    version: str | None = None  # None = latest stable


@router.post("/parse/pypi")
async def start_pypi_parse(
    body: PyPIParseRequest,
    workspace: CurrentWorkspaceDep,
    db: DbDep,
):
    """Validate PyPI package name, create service record, start PyPI parse workflow."""

    package_name = body.packageName.strip()

    # Validate package name
    if not PYPI_PACKAGE_RE.match(package_name):
        raise HTTPException(
            status_code=400,
            detail="Invalid PyPI package name. Use alphanumeric characters, hyphens, underscores, or dots.",
        )

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

    # Create service record
    service = Service(
        project_id=body.projectId,
        name=package_name,
        repo_url=f"https://pypi.org/project/{package_name}/",
        source_type="pypi",
        status="downloading",
    )
    db.add(service)
    await db.commit()
    await db.refresh(service)

    # Start Temporal PyPIParseWorkflow
    workflow_id = f"pypi-parse-{service.id}"
    try:
        client = await get_temporal_client()
        await client.start_workflow(
            "PyPIParseWorkflow",
            {
                "package_name": package_name,
                "version": body.version,
                "user_id": workspace.owner_id,
                "service_id": service.id,
                "command_name": package_name,
                "workspace_id": workspace.id,
            },
            id=workflow_id,
            task_queue="genalpha-parse",
        )

        service.parse_workflow_id = workflow_id
        db.add(service)
        await db.commit()

        logger.info("Started PyPIParseWorkflow %s for %s", workflow_id, package_name)
    except Exception as e:
        logger.error("Failed to start PyPIParseWorkflow: %s", e)
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
        "status": "downloading",
    }
