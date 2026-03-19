from __future__ import annotations
import logging
import time
from typing import Optional
from backend.providers.base import ChatResponse, ProviderBase
from backend.runner.events import EventEmitter
from backend.sanitizer import sanitize_llm_output

logger = logging.getLogger(__name__)


class BaseAgent:
    agent_name: str = "base"

    def __init__(self, provider: ProviderBase, model: str, emitter: EventEmitter) -> None:
        self.provider = provider
        self.model = model
        self.emitter = emitter

    async def call(self, messages: list[dict], job_id: str, system_prompt: Optional[str] = None, temperature: float = 0.7) -> ChatResponse:
        logger.info("[%s] Calling model=%s job=%s input_messages=%d", self.agent_name, self.model, job_id, len(messages))
        start = time.monotonic()
        try:
            response = await self.provider.chat(model=self.model, messages=messages, system_prompt=system_prompt, temperature=temperature)
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("[%s] Error after %.1fs job=%s: %s", self.agent_name, elapsed, job_id, str(e))
            raise
        elapsed = time.monotonic() - start
        response.content = sanitize_llm_output(response.content)
        logger.info("[%s] Response in %.1fs job=%s tokens=%d output_len=%d", self.agent_name, elapsed, job_id, response.usage.total_tokens, len(response.content))
        return response
