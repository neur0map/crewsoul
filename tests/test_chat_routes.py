import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock
from backend.main import create_app
from backend.models import JobStatus
from backend.providers.base import ChatResponse, TokenUsage


@pytest.fixture
def app(tmp_path, sample_config):
    import yaml
    config_path = tmp_path / "config.yml"
    config_path.write_text(yaml.dump(sample_config))
    return create_app(config_path=config_path, output_dir=tmp_path / "output")


@pytest.mark.asyncio
async def test_chat_with_completed_job(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/jobs", json={"character": "Yoda", "search_mode": "normal"})
        job_id = resp.json()["id"]
        job = app.state.queue.get(job_id)
        job.status = JobStatus.TESTING
        job.current_soul_content = "You are Yoda."
        mock_provider = AsyncMock()
        mock_provider.chat.return_value = ChatResponse(content="Hmm. Strong with the Force, you are.", usage=TokenUsage(total_tokens=20), model="gpt-4o-mini")
        app.state.chat_provider = mock_provider
        resp = await client.post(f"/api/chat/{job_id}", json={"message": "Hello Yoda"})
    assert resp.status_code == 200
    assert "response" in resp.json()


@pytest.mark.asyncio
async def test_chat_wrong_status(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/jobs", json={"character": "Yoda", "search_mode": "normal"})
        job_id = resp.json()["id"]
        resp = await client.post(f"/api/chat/{job_id}", json={"message": "Hello"})
    assert resp.status_code == 400
