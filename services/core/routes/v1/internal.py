"""Internal routes — worker callbacks protected by X-Worker-Secret.

These endpoints are called by Temporal worker activities, not by users.
"""

from __future__ import annotations

from fastapi import APIRouter, UploadFile, Form

from services.core.deps import DbDep, WorkerSecretDep, ServiceRepoDep, ArtifactRepoDep
from services.core.exceptions import NotFoundError
from services.core.schemas.common import OkResponse
from services.core.schemas.service import StatusUpdateRequest

router = APIRouter(prefix="/internal", tags=["internal"])

MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB


@router.post("/services/{service_id}/status", response_model=OkResponse)
async def update_service_status(
    service_id: str,
    body: StatusUpdateRequest,
    _auth: WorkerSecretDep,
    service_repo: ServiceRepoDep,
    db: DbDep,
):
    """Update service status — called by Temporal worker activities."""
    service = await service_repo.find_by_id(service_id)
    if not service:
        raise NotFoundError("Service not found")

    fields: dict = {"status": body.status}
    if body.error_message is not None:
        fields["error_message"] = body.error_message
    if body.framework is not None:
        fields["framework"] = body.framework
    if body.route_graph is not None:
        fields["route_graph"] = body.route_graph
    if body.metadata is not None:
        metadata = dict(service.metadata_json or {})
        metadata.update(body.metadata)
        if "artifact_id" in body.metadata:
            fields["artifact_id"] = body.metadata["artifact_id"]
        fields["metadata_json"] = metadata

    await service_repo.update(service, **fields)
    await db.commit()
    return OkResponse()


@router.post("/services/{service_id}/artifacts")
async def upload_artifact(
    *,
    service_id: str,
    file: UploadFile,
    artifact_type: str = Form(...),
    _auth: WorkerSecretDep,
    artifact_repo: ArtifactRepoDep,
    service_repo: ServiceRepoDep,
    db: DbDep,
):
    """Upload artifact — called by Temporal worker after generation."""
    # File size check
    file_data = await file.read()
    if len(file_data) > MAX_UPLOAD_SIZE:
        from services.core.exceptions import ValidationError
        raise ValidationError(f"File too large. Max {MAX_UPLOAD_SIZE // (1024*1024)}MB")

    artifact = await artifact_repo.upsert_for_service(
        service_id=service_id,
        artifact_type=artifact_type,
        filename=file.filename or f"{service_id}.zip",
        file_data=file_data,
        file_size=len(file_data),
    )

    # Update service with artifact_id
    service = await service_repo.find_by_id(service_id)
    if service:
        await service_repo.update(service, artifact_id=artifact.id)

    await db.commit()
    return {"artifact_id": artifact.id, "file_size": artifact.file_size}
