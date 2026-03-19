from __future__ import annotations
import asyncio
import logging
import random
from typing import Optional
import httpx
from backend.providers.base import ChatResponse, ProviderBase, TokenUsage

logger = logging.getLogger(__name__)
BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterProvider(ProviderBase):
    async def chat(self, model: str, messages: list[dict], system_prompt: Optional[str] = None, temperature: float = 0.7) -> ChatResponse:
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages
        payload = {"model": model, "messages": messages, "temperature": temperature}
        data = await self._request("POST", "/chat/completions", payload)
        content = data["choices"][0]["message"]["content"]
        usage_data = data.get("usage", {})
        usage = TokenUsage(prompt_tokens=usage_data.get("prompt_tokens", 0), completion_tokens=usage_data.get("completion_tokens", 0), total_tokens=usage_data.get("total_tokens", 0))
        return ChatResponse(content=content, usage=usage, model=model)

    async def list_models(self) -> list[str]:
        data = await self._request("GET", "/models")
        return sorted([m["id"] for m in data.get("data", [])])

    async def validate_key(self) -> bool:
        try:
            await self._request("GET", "/models")
            return True
        except Exception:
            return False

    async def _request(self, method: str, path: str, json_data: dict | None = None) -> dict:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json", "HTTP-Referer": "https://crewsoul.local", "X-Title": "CrewSoul"}
        for attempt in range(self.max_retries + 1):
            async with httpx.AsyncClient() as client:
                response = await client.request(method, f"{BASE_URL}{path}", headers=headers, json=json_data, timeout=60.0)
            if response.status_code == 429:
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                    logger.warning("Rate limited, retrying in %.1fs (attempt %d/%d)", delay, attempt + 1, self.max_retries)
                    await asyncio.sleep(delay)
                    continue
                raise httpx.HTTPStatusError("Rate limit exceeded after retries", request=response.request, response=response)
            response.raise_for_status()
            return response.json()
        raise RuntimeError("Unreachable")
