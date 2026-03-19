from __future__ import annotations
import logging
import httpx

logger = logging.getLogger(__name__)
PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"


class PerplexitySearch:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def search(self, query: str) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": "sonar", "messages": [{"role": "user", "content": query}]}
        async with httpx.AsyncClient() as client:
            response = await client.post(PERPLEXITY_URL, headers=headers, json=payload, timeout=60.0)
            response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        logger.info("Perplexity search '%s': %d chars", query, len(content))
        return content
