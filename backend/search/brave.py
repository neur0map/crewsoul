from __future__ import annotations
import logging
import httpx

logger = logging.getLogger(__name__)
BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"


class BraveSearch:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def search(self, query: str, count: int = 10) -> list[dict]:
        headers = {"Accept": "application/json", "Accept-Encoding": "gzip", "X-Subscription-Token": self.api_key}
        params = {"q": query, "count": count}
        async with httpx.AsyncClient() as client:
            response = await client.get(BRAVE_URL, headers=headers, params=params, timeout=30.0)
            response.raise_for_status()
        data = response.json()
        results = data.get("web", {}).get("results", [])
        logger.info("Brave search '%s': %d results", query, len(results))
        return [{"title": r.get("title", ""), "url": r.get("url", ""), "description": r.get("description", "")} for r in results]
