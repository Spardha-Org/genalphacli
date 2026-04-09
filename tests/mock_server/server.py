"""Mock API server for testing generated CLIs.

Run with: uv run uvicorn tests.mock_server.server:app --port 9999
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel

app = FastAPI(title="Mock API", version="1.0.0")

# ── In-memory store ────────────────────────────────────────────

USERS: dict[str, dict] = {
    "u1": {"id": "u1", "name": "Alice", "email": "alice@test.com", "role": "admin", "active": True},
    "u2": {"id": "u2", "name": "Bob", "email": "bob@test.com", "role": "user", "active": True},
    "u3": {
        "id": "u3",
        "name": "Charlie",
        "email": "charlie@test.com",
        "role": "user",
        "active": False,
    },
}

PROJECTS: dict[str, dict] = {
    "p1": {"id": "p1", "name": "Alpha Project", "status": "active", "owner_id": "u1"},
    "p2": {"id": "p2", "name": "Beta Project", "status": "completed", "owner_id": "u2"},
}

VALID_TOKEN = "test-token-123"


# ── Models ─────────────────────────────────────────────────────


class UserCreate(BaseModel):
    name: str
    email: str
    role: str = "user"


class ProjectCreate(BaseModel):
    name: str
    owner_id: str


class LoginRequest(BaseModel):
    email: str
    password: str


# ── Auth helper ────────────────────────────────────────────────


def _check_auth(authorization: str | None) -> None:
    if not authorization:
        raise HTTPException(401, "Authentication required. Set MOCKAPI_TOKEN env var.")
    if authorization != f"Bearer {VALID_TOKEN}":
        raise HTTPException(401, "Invalid token.")


# ── Health ─────────────────────────────────────────────────────


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# ── Auth ───────────────────────────────────────────────────────


@app.post("/auth/login")
def login(body: LoginRequest) -> dict:
    """Login and get a token."""
    user = next((u for u in USERS.values() if u["email"] == body.email), None)
    if not user:
        raise HTTPException(401, "Invalid credentials.")
    return {"access_token": VALID_TOKEN, "token_type": "bearer", "user_id": user["id"]}


@app.get("/auth/me")
def get_me(authorization: str | None = Header(None)) -> dict:
    """Get current user from token."""
    _check_auth(authorization)
    return USERS["u1"]


# ── Users ──────────────────────────────────────────────────────


@app.get("/api/v1/users")
def list_users(
    limit: int = Query(10, description="Max results"),
    offset: int = Query(0, description="Pagination offset"),
    authorization: str | None = Header(None),
) -> dict:
    """List all users."""
    _check_auth(authorization)
    all_users = list(USERS.values())
    return {
        "data": all_users[offset : offset + limit],
        "total": len(all_users),
        "limit": limit,
        "offset": offset,
    }


@app.get("/api/v1/users/{user_id}")
def get_user(user_id: str, authorization: str | None = Header(None)) -> dict:
    """Get a user by ID."""
    _check_auth(authorization)
    if user_id not in USERS:
        raise HTTPException(404, f"User {user_id} not found.")
    return USERS[user_id]


@app.post("/api/v1/users")
def create_user(body: UserCreate, authorization: str | None = Header(None)) -> dict:
    """Create a new user."""
    _check_auth(authorization)
    user_id = f"u{uuid4().hex[:6]}"
    user = {
        "id": user_id,
        "name": body.name,
        "email": body.email,
        "role": body.role,
        "active": True,
    }
    USERS[user_id] = user
    return user


@app.delete("/api/v1/users/{user_id}")
def delete_user(user_id: str, authorization: str | None = Header(None)) -> dict:
    """Delete a user."""
    _check_auth(authorization)
    if user_id not in USERS:
        raise HTTPException(404, f"User {user_id} not found.")
    del USERS[user_id]
    return {"deleted": True, "id": user_id}


# ── Projects ───────────────────────────────────────────────────


@app.get("/api/v1/projects")
def list_projects(
    limit: int = Query(10),
    offset: int = Query(0),
    authorization: str | None = Header(None),
) -> dict:
    """List all projects."""
    _check_auth(authorization)
    all_projects = list(PROJECTS.values())
    return {
        "data": all_projects[offset : offset + limit],
        "total": len(all_projects),
    }


@app.get("/api/v1/projects/{project_id}")
def get_project(project_id: str, authorization: str | None = Header(None)) -> dict:
    """Get a project by ID."""
    _check_auth(authorization)
    if project_id not in PROJECTS:
        raise HTTPException(404, f"Project {project_id} not found.")
    return PROJECTS[project_id]


@app.post("/api/v1/projects")
def create_project(body: ProjectCreate, authorization: str | None = Header(None)) -> dict:
    """Create a new project."""
    _check_auth(authorization)
    project_id = f"p{uuid4().hex[:6]}"
    project = {"id": project_id, "name": body.name, "status": "active", "owner_id": body.owner_id}
    PROJECTS[project_id] = project
    return project
