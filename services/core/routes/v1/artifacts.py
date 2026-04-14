"""Artifact routes — download with ownership check."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from services.core.deps import ArtifactRepoDep, CurrentWorkspaceDep
from services.core.exceptions import NotFoundError

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.get("/{artifact_id}/download")
async def download_artifact(artifact_id: str, workspace: CurrentWorkspaceDep, artifact_repo: ArtifactRepoDep):
    """Download an artifact with workspace ownership check."""
    artifact = await artifact_repo.find_by_id_with_ownership(artifact_id, workspace.id)
    if not artifact:
        raise NotFoundError("Artifact not found")

    return Response(
        content=artifact.file_data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{artifact.filename}"'},
    )
