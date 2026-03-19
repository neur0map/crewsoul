"""End-to-end smoke test: create job, verify queue, check API."""
import pytest
import yaml
from httpx import AsyncClient, ASGITransport
from backend.main import create_app


@pytest.fixture
def configured_app(tmp_path, sample_config):
    config_path = tmp_path / "config.yml"
    config_path.write_text(yaml.dump(sample_config))
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return create_app(config_path=config_path, output_dir=output_dir)


@pytest.mark.asyncio
async def test_full_flow_config_and_jobs(configured_app):
    async with AsyncClient(transport=ASGITransport(app=configured_app), base_url="http://test") as client:
        resp = await client.get("/api/config")
        assert resp.status_code == 200
        assert resp.json()["configured"] is True

        resp = await client.post("/api/jobs", json={"character": "Master Yoda", "search_mode": "normal"})
        assert resp.status_code == 200
        yoda_id = resp.json()["id"]

        resp = await client.post("/api/jobs", json={"character": "Obi-Wan Kenobi", "search_mode": "smart"})
        assert resp.status_code == 200

        resp = await client.get("/api/jobs")
        assert len(resp.json()) == 2

        resp = await client.get(f"/api/jobs/{yoda_id}")
        assert resp.json()["character"] == "Master Yoda"
        assert resp.json()["status"] == "QUEUED"

        resp = await client.delete(f"/api/jobs/{yoda_id}")
        assert resp.status_code == 200

        resp = await client.get("/api/jobs")
        assert len(resp.json()) == 1
