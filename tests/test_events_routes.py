import pytest
from backend.main import create_app


@pytest.fixture
def app(tmp_path, sample_config):
    import yaml
    config_path = tmp_path / "config.yml"
    config_path.write_text(yaml.dump(sample_config))
    return create_app(config_path=config_path, output_dir=tmp_path / "output")


def test_sse_endpoint_exists(app):
    """Verify the SSE route is registered in the application."""
    routes = {route.path for route in app.routes}
    assert "/api/events" in routes


def test_sse_endpoint_methods(app):
    """Verify the SSE route accepts GET requests."""
    for route in app.routes:
        if route.path == "/api/events":
            assert "GET" in route.methods
            break
