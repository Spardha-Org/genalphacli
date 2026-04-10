"""Artifact upload and download routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from sqlmodel import select

from services.core.deps import DbDep
from services.core.models import Artifact, Project, Service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["artifacts"])


@router.post("/services/{service_id}/artifacts")
async def upload_artifact(
    service_id: str,
    db: DbDep,
    file: UploadFile = File(...),
    artifact_type: str = Form(...),
):
    """Upload a generated artifact (ZIP) for a service. Called by the worker."""
    result = await db.exec(select(Service).where(Service.id == service_id))
    service = result.first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    if artifact_type not in ("cli", "mcp"):
        raise HTTPException(status_code=400, detail="artifact_type must be 'cli' or 'mcp'")

    file_data = await file.read()

    # Delete previous artifact for this service (latest wins)
    old_result = await db.exec(
        select(Artifact).where(Artifact.service_id == service_id)
    )
    for old in old_result.all():
        await db.delete(old)

    artifact = Artifact(
        service_id=service_id,
        artifact_type=artifact_type,
        filename=file.filename or f"{service.name}.zip",
        file_data=file_data,
        file_size=len(file_data),
    )
    db.add(artifact)

    # Update service to point to this artifact
    service.artifact_id = artifact.id
    db.add(service)

    await db.commit()
    await db.refresh(artifact)

    logger.info("Artifact %s uploaded for service %s (%d bytes)", artifact.id, service_id, artifact.file_size)
    return {"artifact_id": artifact.id, "file_size": artifact.file_size}


@router.get("/artifacts/{artifact_id}/download")
async def download_artifact(
    artifact_id: str,
    db: DbDep,
):
    """Download a generated artifact ZIP."""
    result = await db.exec(select(Artifact).where(Artifact.id == artifact_id))
    artifact = result.first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    return Response(
        content=artifact.file_data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{artifact.filename}"'},
    )
