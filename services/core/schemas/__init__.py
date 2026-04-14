"""Pydantic request/response schemas — the API contract."""

from services.core.schemas.common import PaginatedResponse
from services.core.schemas.auth import (
    MagicLinkRequest,
    MagicLinkResponse,
    VerifyResponse,
    SessionResponse,
    UserResponse,
    WorkspaceResponse,
)
from services.core.schemas.project import (
    CreateProjectRequest,
    UpdateProjectRequest,
    ProjectResponse,
)
from services.core.schemas.service import (
    ServiceResponse,
    ServiceListItem,
    AuthConfigRequest,
    StatusUpdateRequest,
)
from services.core.schemas.parse import (
    ParseRequest,
    PyPIParseRequest,
    ParseResponse,
)
from services.core.schemas.generate import (
    GenerateRequest,
    PublishRequest,
    GenerateResponse,
)
from services.core.schemas.integration import (
    InstallRequest,
    ConnectRequest,
    AppResponse,
    IntegrationResponse,
)
