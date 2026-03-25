import pytest
import yaml
from httpx import AsyncClient, ASGITransport
from backend.main import create_app
from backend.models import JobStatus

@pytest.fixture
def app(tmp_path, sample_config):
    config_path = tmp_path / "config.yml"
    config_path.write_text(yaml.dump(sample_config))
    return create_app(config_path=config_path, output_dir=tmp_path / "output")

@pytest.mark.asyncio
async def test_patch_profile_reference_samples(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/jobs", json={"character": "Yoda", "search_mode": "normal"})
        job_id = resp.json()["id"]
        job = app.state.queue.get(job_id)
        job.status = JobStatus.READY
        job.personality_profile = {"speech_patterns": {}}
        app.state.queue.persist(job)
        resp = await client.patch(f"/api/jobs/{job_id}/profile", json={"reference_samples": ["Do or do not.", "Fear leads to anger."]})
    assert resp.status_code == 200
    assert resp.json()["personality_profile"]["reference_samples"] == ["Do or do not.", "Fear leads to anger."]

@pytest.mark.asyncio
async def test_patch_profile_score_weights(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/jobs", json={"character": "Yoda", "search_mode": "normal"})
        job_id = resp.json()["id"]
        job = app.state.queue.get(job_id)
        job.status = JobStatus.READY
        job.personality_profile = {"speech_patterns": {}}
        app.state.queue.persist(job)
        resp = await client.patch(f"/api/jobs/{job_id}/profile", json={"score_weights": {"character": 2.0, "speech": 1.5}})
    assert resp.status_code == 200
    assert resp.json()["personality_profile"]["score_weights"]["character"] == 2.0

@pytest.mark.asyncio
async def test_patch_profile_rejects_non_ready(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/jobs", json={"character": "Yoda", "search_mode": "normal"})
        job_id = resp.json()["id"]
        resp = await client.patch(f"/api/jobs/{job_id}/profile", json={"reference_samples": ["test"]})
    assert resp.status_code == 400

@pytest.mark.asyncio
async def test_patch_profile_rejects_invalid_weight_keys(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/jobs", json={"character": "Yoda", "search_mode": "normal"})
        job_id = resp.json()["id"]
        job = app.state.queue.get(job_id)
        job.status = JobStatus.READY
        job.personality_profile = {"speech_patterns": {}}
        app.state.queue.persist(job)
        resp = await client.patch(f"/api/jobs/{job_id}/profile", json={"score_weights": {"made_up_dimension": 2.0}})
    assert resp.status_code == 400
