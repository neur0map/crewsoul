from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class ChatResponse:
    content: str
    usage: TokenUsage
    model: str = ""


class ProviderBase(ABC):
    def __init__(self, api_key: str, max_retries: int = 3, base_delay: float = 1.0) -> None:
        self.api_key = api_key
        self.max_retries = max_retries
        self.base_delay = base_delay

    @abstractmethod
    async def chat(self, model: str, messages: list[dict], system_prompt: Optional[str] = None, temperature: float = 0.7) -> ChatResponse: ...

    @abstractmethod
    async def list_models(self) -> list[str]: ...

    @abstractmethod
    async def validate_key(self) -> bool: ...
