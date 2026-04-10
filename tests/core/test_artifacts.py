"""Tests for artifact upload, download, and service limit removal."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


class TestServiceLimitRemoved:
    """Verify the 2-service-per-workspace limit no longer exists."""

    async def test_can_parse_more_than_two_services(self, client, seed_data):
        """Creating 3+ services should succeed (no 429 error)."""
        project_id = seed_data["project"].id

        for i in range(5):
            resp = await client.post(
                "/parse",
                json={
                    "repoUrl": f"https://github.com/test/repo-{i}",
                    "projectId": project_id,
                },
            )
            # Should either succeed (starting parse) or fail for reasons
            # OTHER than the service limit (e.g., Temporal not running).
            # The key assertion: never 429.
            assert resp.status_code != 429, f"Got 429 on service {i} — limit still enforced!"


class TestArtifactUpload:
    """Tests for POST /services/{service_id}/artifacts."""

    async def test_upload_artifact_success(self, client, seed_data):
        """Upload a ZIP artifact for a service."""
        service_id = seed_data["service"].id
        zip_content = b"PK\x03\x04fake-zip-content-for-testing"

        resp = await client.post(
            f"/services/{service_id}/artifacts",
            files={"file": ("test-api.zip", zip_content, "application/zip")},
            data={"artifact_type": "cli"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "artifact_id" in data
        assert data["file_size"] == len(zip_content)

    async def test_upload_artifact_invalid_type(self, client, seed_data):
        """Upload with invalid artifact_type should fail."""
        service_id = seed_data["service"].id

        resp = await client.post(
            f"/services/{service_id}/artifacts",
            files={"file": ("test.zip", b"fake", "application/zip")},
            data={"artifact_type": "invalid"},
        )

        assert resp.status_code == 400
        assert "artifact_type" in resp.json()["detail"]

    async def test_upload_artifact_nonexistent_service(self, client):
        """Upload to a non-existent service should 404."""
        resp = await client.post(
            "/services/nonexistent/artifacts",
            files={"file": ("test.zip", b"fake", "application/zip")},
            data={"artifact_type": "cli"},
        )

        assert resp.status_code == 404

    async def test_upload_replaces_previous_artifact(self, client, seed_data):
        """Re-uploading should replace the old artifact (latest wins)."""
        service_id = seed_data["service"].id

        # First upload
        resp1 = await client.post(
            f"/services/{service_id}/artifacts",
            files={"file": ("v1.zip", b"version-1-content", "application/zip")},
            data={"artifact_type": "cli"},
        )
        assert resp1.status_code == 200
        artifact_id_1 = resp1.json()["artifact_id"]

        # Second upload
        resp2 = await client.post(
            f"/services/{service_id}/artifacts",
            files={"file": ("v2.zip", b"version-2-content-longer", "application/zip")},
            data={"artifact_type": "cli"},
        )
        assert resp2.status_code == 200
        artifact_id_2 = resp2.json()["artifact_id"]

        # IDs should differ
        assert artifact_id_1 != artifact_id_2

        # Old artifact should be gone
        resp_old = await client.get(f"/artifacts/{artifact_id_1}/download")
        assert resp_old.status_code == 404

        # New artifact should work
        resp_new = await client.get(f"/artifacts/{artifact_id_2}/download")
        assert resp_new.status_code == 200
        assert resp_new.content == b"version-2-content-longer"


class TestArtifactDownload:
    """Tests for GET /artifacts/{artifact_id}/download."""

    async def test_download_artifact(self, client, seed_data):
        """Download a previously uploaded artifact."""
        service_id = seed_data["service"].id
        zip_content = b"PK\x03\x04real-zip-bytes-here"

        # Upload first
        upload_resp = await client.post(
            f"/services/{service_id}/artifacts",
            files={"file": ("test-api.zip", zip_content, "application/zip")},
            data={"artifact_type": "cli"},
        )
        artifact_id = upload_resp.json()["artifact_id"]

        # Download
        resp = await client.get(f"/artifacts/{artifact_id}/download")

        assert resp.status_code == 200
        assert resp.content == zip_content
        assert resp.headers["content-type"] == "application/zip"
        assert "test-api.zip" in resp.headers["content-disposition"]

    async def test_download_nonexistent_artifact(self, client):
        """Downloading a non-existent artifact should 404."""
        resp = await client.get("/artifacts/nonexistent/download")
        assert resp.status_code == 404


class TestServiceDownloadWithArtifact:
    """Tests for the legacy GET /services/{id}/download endpoint using artifacts."""

    async def test_download_via_service_endpoint(self, client, seed_data):
        """The legacy /services/{id}/download should serve from the artifact."""
        service_id = seed_data["service"].id
        zip_content = b"PK\x03\x04legacy-download-test"

        # Upload artifact
        upload_resp = await client.post(
            f"/services/{service_id}/artifacts",
            files={"file": ("test-api.zip", zip_content, "application/zip")},
            data={"artifact_type": "cli"},
        )
        assert upload_resp.status_code == 200

        # Download via legacy endpoint
        resp = await client.get(f"/services/{service_id}/download")

        assert resp.status_code == 200
        assert resp.content == zip_content

    async def test_download_no_artifact(self, client, seed_data):
        """Service without artifact_id should return 400."""
        service_id = seed_data["service"].id

        resp = await client.get(f"/services/{service_id}/download")
        assert resp.status_code == 400
        assert "Generate first" in resp.json()["detail"]


class TestServiceDeleteCascadesArtifacts:
    """Deleting a service should also delete its artifacts."""

    async def test_delete_service_removes_artifact(self, client, seed_data):
        """After deleting a service, its artifact should be gone."""
        service_id = seed_data["service"].id

        # Upload artifact
        upload_resp = await client.post(
            f"/services/{service_id}/artifacts",
            files={"file": ("test.zip", b"delete-me", "application/zip")},
            data={"artifact_type": "cli"},
        )
        artifact_id = upload_resp.json()["artifact_id"]

        # Delete service
        del_resp = await client.delete(f"/services/{service_id}")
        assert del_resp.status_code == 200

        # Artifact should be gone
        resp = await client.get(f"/artifacts/{artifact_id}/download")
        assert resp.status_code == 404


class TestStatusUpdateWithArtifactId:
    """Tests for the status update endpoint handling artifact_id metadata."""

    async def test_status_update_sets_artifact_id(self, client, seed_data):
        """POST /services/{id}/status with artifact_id in metadata should set it on the service."""
        service_id = seed_data["service"].id

        resp = await client.post(
            f"/services/{service_id}/status",
            json={
                "status": "complete",
                "metadata": {"artifact_id": "art-123", "file_size": 4096},
            },
        )
        assert resp.status_code == 200

        # Verify artifact_id is set on the service
        svc_resp = await client.get(f"/services/{service_id}")
        assert svc_resp.status_code == 200
        assert svc_resp.json()["artifact_id"] == "art-123"

    async def test_status_update_without_artifact_id(self, client, seed_data):
        """Status update without artifact_id should not break."""
        service_id = seed_data["service"].id

        resp = await client.post(
            f"/services/{service_id}/status",
            json={"status": "parsing"},
        )
        assert resp.status_code == 200


class TestServiceDetailResponse:
    """Tests for GET /services/{id} response shape."""

    async def test_service_response_includes_artifact_id(self, client, seed_data):
        """Service detail should include artifact_id field."""
        service_id = seed_data["service"].id

        resp = await client.get(f"/services/{service_id}")
        assert resp.status_code == 200

        data = resp.json()
        assert "artifact_id" in data
        assert data["artifact_id"] is None  # No artifact uploaded yet
