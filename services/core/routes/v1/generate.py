"""Generate and publish routes."""

from __future__ import annotations

from fastapi import APIRouter

from services.core.deps import CurrentWorkspaceDep, GenerateServiceDep
from services.core.schemas.generate import GenerateRequest, GenerateResponse, PublishRequest

router = APIRouter(tags=["generate"])


@router.post("/generate", response_model=GenerateResponse)
async def start_generate(body: GenerateRequest, workspace: CurrentWorkspaceDep, generate_service: GenerateServiceDep):
    result = await generate_service.start_generate(
        body.service_id, body.output_types, body.cli_name, body.base_url, workspace,
    )
    return GenerateResponse(service_id=result.service_id, workflow_id=result.workflow_id, status=result.status)


@router.post("/publish", response_model=GenerateResponse)
async def start_publish(body: PublishRequest, workspace: CurrentWorkspaceDep, generate_service: GenerateServiceDep):
    result = await generate_service.start_publish(
        body.service_id, body.output_types, body.cli_name, body.base_url, workspace,
    )
    return GenerateResponse(service_id=result.service_id, workflow_id=result.workflow_id, status=result.status)
