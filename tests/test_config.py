import pytest
from pathlib import Path
from backend.config import (
    AppConfig,
    load_config,
    save_config,
    redact_keys,
    validate_config,
)


def test_load_config_from_file(tmp_path: Path, sample_config: dict):
    import yaml
    config_path = tmp_path / "crewsoul.config.yml"
    config_path.write_text(yaml.dump(sample_config))
    config = load_config(config_path)
    assert config.provider.active == "openai"
    assert config.provider.openai.models.judge == "gpt-4o"
    assert config.orchestration.score_threshold == 0.9


def test_load_config_missing_file(tmp_path: Path):
    config_path = tmp_path / "nonexistent.yml"
    config = load_config(config_path)
    assert config is None


def test_save_config(tmp_path: Path, sample_config: dict):
    import yaml
    config_path = tmp_path / "crewsoul.config.yml"
    config = AppConfig(**sample_config)
    save_config(config, config_path)
    loaded = yaml.safe_load(config_path.read_text())
    assert loaded["provider"]["active"] == "openai"


def test_redact_keys(sample_config: dict):
    config = AppConfig(**sample_config)
    redacted = redact_keys(config)
    assert redacted["provider"]["openai"]["api_key"] == "••••2345"
    assert redacted["search"]["brave"]["api_key"] == "•••••key"
    assert redacted["search"]["perplexity"]["api_key"] == ""


def test_validate_config_valid(sample_config: dict):
    config = AppConfig(**sample_config)
    errors = validate_config(config)
    assert errors == []


def test_validate_config_no_provider_key(sample_config: dict):
    sample_config["provider"]["openai"]["api_key"] = ""
    config = AppConfig(**sample_config)
    errors = validate_config(config)
    assert any("api_key" in e for e in errors)


def test_validate_config_no_search_keys(sample_config: dict):
    sample_config["search"]["brave"]["api_key"] = ""
    sample_config["search"]["perplexity"]["api_key"] = ""
    config = AppConfig(**sample_config)
    errors = validate_config(config)
    assert any("search" in e.lower() for e in errors)
