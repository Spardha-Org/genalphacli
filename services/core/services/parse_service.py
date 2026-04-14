"""Parse service — strategy pattern for GitHub/PyPI workflows."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from sqlmodel.ext.asyncio.session import AsyncSession

from services.core.clients.temporal_client import TemporalClient
from services.core.clients.tps_client import TpsHttpClient
from services.core.exceptions import NotFoundError, ValidationError
from services.core.models import Service, Workspace
from services.core.repositories.project_repo import ProjectRepository
from services.core.repositories.service_repo import ServiceRepository

logger = logging.getLogger(__name__)

GITHUB_URL_RE = re.compile(
    r"^https://github\.com/([a-zA-Z0-9._-]+)/([a-zA-Z0-9._-]+?)(?:\.git)?/?$"
)


@dataclass
class WorkflowConfig:
    workflow_name: str
    task_queue: str = "genalpha-parse"


# Strategy: source_type → workflow config
PARSE_STRATEGIES: dict[str, WorkflowConfig] = {
    "github": WorkflowConfig(workflow_name="ParseWorkflow"),
    "pypi": WorkflowConfig(workflow_name="PyPIParseWorkflow"),
}


@dataclass
class ParseResult:
    service_id: str
    workflow_id: str
    status: str


class ParseService:
    def __init__(
        self,
        db: AsyncSession,
        services: ServiceRepository,
        projects: ProjectRepository,
        tps: TpsHttpClient,
        temporal: TemporalClient,
    ):
        self._db = db
        self._services = services
        self._projects = projects
        self._tps = tps
        self._temporal = temporal

    async def start_github_parse(
        self, repo_url: str, project_id: str, workspace: Workspace
    ) -> ParseResult:
        """Parse a GitHub repo."""
        match = GITHUB_URL_RE.match(repo_url.strip())
        if not match:
            raise ValidationError("Invalid GitHub URL")

        owner, repo = match.group(1), match.group(2)

        project = await self._projects.find_by_id_in_workspace(project_id, workspace.id)
        if not project:
            raise NotFoundError("Project not found")

        # Look up GitHub integration for authenticated clone
        integration = await self._tps.get_integration(workspace.owner_id, "github")
        integration_id = integration["id"] if integration else ""

        # Create service
        service = await self._services.create(
            project_id=project_id,
            name=repo,
            repo_url=repo_url.strip(),
            source_type="github",
            status="cloning",
        )

        # Start workflow
        config = PARSE_STRATEGIES["github"]
        workflow_id = await self._temporal.start_workflow(
            config.workflow_name,
            {
                "owner": owner,
                "repo": repo,
                "user_id": workspace.owner_id,
                "service_id": service.id,
                "command_name": repo,
                "workspace_id": workspace.id,
                "integration_id": integration_id,
            },
            service_id=service.id,
            prefix="parse",
            task_queue=config.task_queue,
        )

        await self._services.update(service, parse_workflow_id=workflow_id)
        await self._db.commit()

        return ParseResult(service_id=service.id, workflow_id=workflow_id, status="cloning")

    async def start_pypi_parse(
        self, package_name: str, project_id: str, workspace: Workspace,
        version: str | None = None,
    ) -> ParseResult:
        """Parse a PyPI package."""
        project = await self._projects.find_by_id_in_workspace(project_id, workspace.id)
        if not project:
            raise NotFoundError("Project not found")

        service = await self._services.create(
            project_id=project_id,
            name=package_name,
            repo_url=f"https://pypi.org/project/{package_name}/",
            source_type="pypi",
            status="downloading",
        )

        config = PARSE_STRATEGIES["pypi"]
        workflow_id = await self._temporal.start_workflow(
            config.workflow_name,
            {
                "package_name": package_name,
                "version": version,
                "user_id": workspace.owner_id,
                "service_id": service.id,
                "command_name": package_name,
                "workspace_id": workspace.id,
            },
            service_id=service.id,
            prefix="pypi-parse",
            task_queue=config.task_queue,
        )

        await self._services.update(service, parse_workflow_id=workflow_id)
        await self._db.commit()

        return ParseResult(service_id=service.id, workflow_id=workflow_id, status="downloading")
