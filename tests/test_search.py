import pytest
from backend.search.brave import BraveSearch
from backend.search.perplexity import PerplexitySearch


@pytest.mark.asyncio
async def test_brave_search(httpx_mock):
    httpx_mock.add_response(
        url="https://api.search.brave.com/res/v1/web/search",
        json={"web": {"results": [
            {"title": "Yoda Wiki", "url": "https://example.com", "description": "Yoda is a character"},
            {"title": "Yoda Speech", "url": "https://example2.com", "description": "Inverted syntax"},
        ]}},
    )
    client = BraveSearch(api_key="bv-test")
    results = await client.search("Master Yoda personality traits")
    assert len(results) == 2
    assert results[0]["title"] == "Yoda Wiki"


@pytest.mark.asyncio
async def test_brave_search_empty(httpx_mock):
    httpx_mock.add_response(url="https://api.search.brave.com/res/v1/web/search", json={"web": {"results": []}})
    client = BraveSearch(api_key="bv-test")
    results = await client.search("completely obscure query")
    assert results == []


@pytest.mark.asyncio
async def test_perplexity_search(httpx_mock):
    httpx_mock.add_response(
        url="https://api.perplexity.ai/chat/completions",
        json={"choices": [{"message": {"content": "Master Yoda is a 900-year-old Jedi Master..."}}]},
    )
    client = PerplexitySearch(api_key="pplx-test")
    result = await client.search("Master Yoda personality analysis")
    assert "Yoda" in result
