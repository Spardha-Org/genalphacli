"""Parse routes — GitHub and PyPI."""

from __future__ import annotations

from fastapi import APIRouter

from services.core.deps import CurrentWorkspaceDep, ParseServiceDep
from services.core.schemas.parse import ParseRequest, ParseResponse, PyPIParseRequest

router = APIRouter(tags=["parse"])


@router.post("/parse", response_model=ParseResponse)
async def start_parse(body: ParseRequest, workspace: CurrentWorkspaceDep, parse_service: ParseServiceDep):
    result = await parse_service.start_github_parse(body.repo_url, body.project_id, workspace)
    return ParseResponse(serviceId=result.service_id, workflowId=result.workflow_id, status=result.status)


@router.post("/parse/pypi", response_model=ParseResponse)
async def start_pypi_parse(body: PyPIParseRequest, workspace: CurrentWorkspaceDep, parse_service: ParseServiceDep):
    result = await parse_service.start_pypi_parse(body.package_name, body.project_id, workspace, body.version)
    return ParseResponse(serviceId=result.service_id, workflowId=result.workflow_id, status=result.status)
