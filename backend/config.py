from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class ModelAssignment:
    judge: str = ""
    target: str = ""
    converser: str = ""
    fetcher: str = ""
    researcher: str = ""


@dataclass
class ProviderConfig:
    api_key: str = ""
    models: ModelAssignment = field(default_factory=ModelAssignment)

    def __post_init__(self):
        if isinstance(self.models, dict):
            self.models = ModelAssignment(**self.models)


@dataclass
class ProviderSettings:
    active: str = "openai"
    openai: ProviderConfig = field(default_factory=ProviderConfig)
    openrouter: ProviderConfig = field(default_factory=ProviderConfig)

    def __post_init__(self):
        if isinstance(self.openai, dict):
            self.openai = ProviderConfig(**self.openai)
        if isinstance(self.openrouter, dict):
            self.openrouter = ProviderConfig(**self.openrouter)

    def active_config(self) -> ProviderConfig:
        return getattr(self, self.active)


@dataclass
class SearchKeyConfig:
    api_key: str = ""


@dataclass
class SearchSettings:
    brave: SearchKeyConfig = field(default_factory=SearchKeyConfig)
    perplexity: SearchKeyConfig = field(default_factory=SearchKeyConfig)

    def __post_init__(self):
        if isinstance(self.brave, dict):
            self.brave = SearchKeyConfig(**self.brave)
        if isinstance(self.perplexity, dict):
            self.perplexity = SearchKeyConfig(**self.perplexity)


@dataclass
class OrchestrationSettings:
    questions_per_loop: int = 6
    tone_rotation: str = "per_question"
    score_threshold: float = 0.9
    max_loops: int = 15
    plateau_window: int = 3
    soul_max_words: int = 2000


@dataclass
class OutputSettings:
    directory: str = "./output"


@dataclass
class LeakDetectorSettings:
    hard_match_score: float = 0.0
    soft_match_penalty: float = 0.15
    soft_match_floor: float = 0.2


@dataclass
class ScoringSettings:
    llm_calls: int = 2
    divergence_threshold: float = 0.3
    leak_detector: LeakDetectorSettings = field(default_factory=LeakDetectorSettings)

    def __post_init__(self):
        if isinstance(self.leak_detector, dict):
            self.leak_detector = LeakDetectorSettings(**self.leak_detector)


@dataclass
class AppConfig:
    provider: ProviderSettings = field(default_factory=ProviderSettings)
    search: SearchSettings = field(default_factory=SearchSettings)
    orchestration: OrchestrationSettings = field(default_factory=OrchestrationSettings)
    output: OutputSettings = field(default_factory=OutputSettings)
    scoring: ScoringSettings = field(default_factory=ScoringSettings)

    def __post_init__(self):
        if isinstance(self.provider, dict):
            self.provider = ProviderSettings(**self.provider)
        if isinstance(self.search, dict):
            self.search = SearchSettings(**self.search)
        if isinstance(self.orchestration, dict):
            self.orchestration = OrchestrationSettings(**self.orchestration)
        if isinstance(self.output, dict):
            self.output = OutputSettings(**self.output)
        if isinstance(self.scoring, dict):
            self.scoring = ScoringSettings(**self.scoring)


def load_config(path: Path) -> Optional[AppConfig]:
    if not path.exists():
        return None
    data = yaml.safe_load(path.read_text())
    return AppConfig(**data)


def save_config(config: AppConfig, path: Path) -> None:
    data = _to_dict(config)
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))


def _to_dict(obj) -> dict:
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _to_dict(v) for k, v in obj.__dict__.items()}
    return obj


def redact_keys(config: AppConfig) -> dict:
    data = _to_dict(config)
    _redact_recursive(data)
    return data


def _redact_recursive(d: dict) -> None:
    for key, value in d.items():
        if isinstance(value, dict):
            _redact_recursive(value)
        elif key == "api_key" and isinstance(value, str) and value:
            # Show last segment (after final '-'), capped at 4 chars;
            # prefix with bullets to reach a total of 8 display chars.
            last_segment = value.split("-")[-1] if "-" in value else value
            visible = last_segment[-4:]
            bullets = 8 - len(visible)
            d[key] = "•" * bullets + visible


def validate_config(config: AppConfig) -> list[str]:
    errors = []
    active = config.provider.active_config()
    if not active.api_key:
        errors.append(f"Active provider '{config.provider.active}' has no api_key")
    if not config.search.brave.api_key and not config.search.perplexity.api_key:
        errors.append("At least one search provider (Brave or Perplexity) requires an api_key")
    return errors
