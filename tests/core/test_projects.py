"""Tests for project CRUD endpoints."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


class TestListProjects:
    """GET /projects"""

    async def test_list_returns_seeded_project(self, client, seed_data):
        resp = await client.get("/projects")
        assert resp.status_code == 200
        projects = resp.json()
        assert len(projects) == 1
        assert projects[0]["name"] == "Test Project"
        assert projects[0]["id"] == seed_data["project"].id

    async def test_list_returns_empty_when_no_projects(self, client, db, seed_data):
        """After deleting the seeded project, list should be empty."""
        await client.delete(f"/projects/{seed_data['project'].id}")
        resp = await client.get("/projects")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_response_shape(self, client, seed_data):
        """Each project should have id, name, description, created_at."""
        resp = await client.get("/projects")
        project = resp.json()[0]
        assert "id" in project
        assert "name" in project
        assert "description" in project
        assert "created_at" in project

    async def test_list_only_shows_workspace_projects(self, client, db, seed_data):
        """Projects from other workspaces should not appear."""
        from services.core.models import Project

        # Create a project in a different workspace
        other_project = Project(
            id="other-proj",
            workspace_id="other-ws-id",
            name="Other Project",
        )
        db.add(other_project)
        await db.commit()

        resp = await client.get("/projects")
        assert resp.status_code == 200
        projects = resp.json()
        assert len(projects) == 1
        assert projects[0]["id"] == seed_data["project"].id


class TestCreateProject:
    """POST /projects"""

    async def test_create_project_success(self, client):
        resp = await client.post(
            "/projects",
            json={"name": "My New Project", "description": "A test project"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "My New Project"
        assert data["description"] == "A test project"
        assert "id" in data
        assert "created_at" in data

    async def test_create_project_without_description(self, client):
        resp = await client.post(
            "/projects",
            json={"name": "No Desc Project"},
        )
        assert resp.status_code == 200
        assert resp.json()["description"] is None

    async def test_create_project_strips_whitespace(self, client):
        resp = await client.post(
            "/projects",
            json={"name": "  Spaced Name  "},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Spaced Name"

    async def test_create_project_appears_in_list(self, client):
        await client.post("/projects", json={"name": "Listed Project"})
        resp = await client.get("/projects")
        names = [p["name"] for p in resp.json()]
        assert "Listed Project" in names

    async def test_create_multiple_projects(self, client):
        await client.post("/projects", json={"name": "Project A"})
        await client.post("/projects", json={"name": "Project B"})
        await client.post("/projects", json={"name": "Project C"})

        resp = await client.get("/projects")
        # seed_data has 1 project + 3 new = 4
        assert len(resp.json()) == 4

    async def test_create_project_missing_name_fails(self, client):
        resp = await client.post("/projects", json={})
        assert resp.status_code == 422  # validation error

    async def test_create_project_empty_name(self, client):
        """Empty string name should still create (no server-side validation beyond strip)."""
        resp = await client.post("/projects", json={"name": ""})
        assert resp.status_code == 200


class TestDeleteProject:
    """DELETE /projects/{project_id}"""

    async def test_delete_project_success(self, client, seed_data):
        project_id = seed_data["project"].id
        resp = await client.delete(f"/projects/{project_id}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    async def test_delete_project_removes_from_list(self, client, seed_data):
        project_id = seed_data["project"].id
        await client.delete(f"/projects/{project_id}")

        resp = await client.get("/projects")
        assert len(resp.json()) == 0

    async def test_delete_nonexistent_project(self, client):
        resp = await client.delete("/projects/nonexistent-id")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    async def test_delete_project_from_other_workspace(self, client, db):
        """Cannot delete a project that belongs to a different workspace."""
        from services.core.models import Project

        other_project = Project(
            id="other-ws-proj",
            workspace_id="some-other-ws",
            name="Not Mine",
        )
        db.add(other_project)
        await db.commit()

        resp = await client.delete("/projects/other-ws-proj")
        assert resp.status_code == 404

    async def test_delete_project_cascades_services(self, client, seed_data):
        """Deleting a project should also delete its services."""
        project_id = seed_data["project"].id
        service_id = seed_data["service"].id

        # Service exists before delete
        svc_resp = await client.get(f"/services/{service_id}")
        assert svc_resp.status_code == 200

        # Delete project
        await client.delete(f"/projects/{project_id}")

        # Service should be gone
        svc_resp = await client.get(f"/services/{service_id}")
        assert svc_resp.status_code == 404

    async def test_delete_is_idempotent(self, client, seed_data):
        """Deleting the same project twice should 404 on second attempt."""
        project_id = seed_data["project"].id
        resp1 = await client.delete(f"/projects/{project_id}")
        assert resp1.status_code == 200

        resp2 = await client.delete(f"/projects/{project_id}")
        assert resp2.status_code == 404
