import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import create_app


@pytest.fixture
def app(tmp_path):
    return create_app(config_path=tmp_path / "config.yml", output_dir=tmp_path / "output")


@pytest.mark.asyncio
async def test_get_config_no_config(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/config")
    assert resp.status_code == 200
    assert resp.json()["configured"] is False


@pytest.mark.asyncio
async def test_save_and_get_config(app, sample_config):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/config", json=sample_config)
        assert resp.status_code == 200
        resp = await client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["configured"] is True
