import pytest
import yaml
from httpx import AsyncClient, ASGITransport
from backend.main import create_app


@pytest.fixture
def app(tmp_path, sample_config):
    config_path = tmp_path / "config.yml"
    config_path.write_text(yaml.dump(sample_config))
    return create_app(config_path=config_path, output_dir=tmp_path / "output")


@pytest.mark.asyncio
async def test_create_job(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/jobs", json={"character": "Master Yoda", "search_mode": "normal"})
    assert resp.status_code == 200
    assert resp.json()["character"] == "Master Yoda"
    assert resp.json()["status"] == "QUEUED"


@pytest.mark.asyncio
async def test_list_jobs(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/jobs", json={"character": "Yoda", "search_mode": "normal"})
        await client.post("/api/jobs", json={"character": "Obi-Wan", "search_mode": "smart"})
        resp = await client.get("/api/jobs")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_get_job(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post("/api/jobs", json={"character": "Yoda", "search_mode": "normal"})
        job_id = create_resp.json()["id"]
        resp = await client.get(f"/api/jobs/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["character"] == "Yoda"


@pytest.mark.asyncio
async def test_delete_job(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post("/api/jobs", json={"character": "Yoda", "search_mode": "normal"})
        job_id = create_resp.json()["id"]
        resp = await client.delete(f"/api/jobs/{job_id}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_nonexistent_job(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/jobs/fake-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_job(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/jobs", json={"character": "Yoda", "search_mode": "normal"})
        job_id = resp.json()["id"]
        resp = await client.patch(f"/api/jobs/{job_id}", json={"search_mode": "smart"})
    assert resp.status_code == 200
    assert resp.json()["search_mode"] == "smart"


@pytest.mark.asyncio
async def test_get_logs(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/jobs", json={"character": "Yoda", "search_mode": "normal"})
        job_id = resp.json()["id"]
        resp = await client.get(f"/api/jobs/{job_id}/logs")
    assert resp.status_code == 200
    assert resp.json()["entries"] == []


@pytest.mark.asyncio
async def test_get_diff(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/jobs", json={"character": "Yoda", "search_mode": "normal"})
        job_id = resp.json()["id"]
        resp = await client.get(f"/api/jobs/{job_id}/diff")
    assert resp.status_code == 200
    assert resp.json()["entries"] == []


@pytest.mark.asyncio
async def test_get_artifacts_no_output(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/jobs", json={"character": "Yoda", "search_mode": "normal"})
        job_id = resp.json()["id"]
        resp = await client.get(f"/api/jobs/{job_id}/artifacts")
    assert resp.status_code == 404
