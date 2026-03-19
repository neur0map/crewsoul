import pytest
import httpx
from backend.providers.base import ProviderBase
from backend.providers.openai_provider import OpenAIProvider
from backend.providers.openrouter_provider import OpenRouterProvider


def test_provider_base_is_abstract():
    with pytest.raises(TypeError):
        ProviderBase(api_key="test")


@pytest.mark.asyncio
async def test_openai_chat(httpx_mock):
    httpx_mock.add_response(
        url="https://api.openai.com/v1/chat/completions",
        json={
            "choices": [{"message": {"content": "Hello from GPT"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        },
    )
    provider = OpenAIProvider(api_key="sk-test")
    result = await provider.chat(model="gpt-4o-mini", messages=[{"role": "user", "content": "Hi"}])
    assert result.content == "Hello from GPT"
    assert result.usage.total_tokens == 15


@pytest.mark.asyncio
async def test_openai_chat_with_system(httpx_mock):
    httpx_mock.add_response(
        url="https://api.openai.com/v1/chat/completions",
        json={
            "choices": [{"message": {"content": "I am Yoda"}}],
            "usage": {"prompt_tokens": 20, "completion_tokens": 5, "total_tokens": 25},
        },
    )
    provider = OpenAIProvider(api_key="sk-test")
    result = await provider.chat(
        model="gpt-4o", messages=[{"role": "user", "content": "Who are you?"}],
        system_prompt="You are Yoda.",
    )
    assert result.content == "I am Yoda"


@pytest.mark.asyncio
async def test_openai_rate_limit_retry(httpx_mock):
    httpx_mock.add_response(url="https://api.openai.com/v1/chat/completions", status_code=429, headers={"retry-after": "1"})
    httpx_mock.add_response(
        url="https://api.openai.com/v1/chat/completions",
        json={"choices": [{"message": {"content": "OK after retry"}}], "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}},
    )
    provider = OpenAIProvider(api_key="sk-test", max_retries=2, base_delay=0.01)
    result = await provider.chat(model="gpt-4o-mini", messages=[{"role": "user", "content": "Hi"}])
    assert result.content == "OK after retry"


@pytest.mark.asyncio
async def test_openrouter_chat(httpx_mock):
    httpx_mock.add_response(
        url="https://openrouter.ai/api/v1/chat/completions",
        json={"choices": [{"message": {"content": "Hello from OpenRouter"}}], "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}},
    )
    provider = OpenRouterProvider(api_key="or-test")
    result = await provider.chat(model="anthropic/claude-3.5-sonnet", messages=[{"role": "user", "content": "Hi"}])
    assert result.content == "Hello from OpenRouter"


@pytest.mark.asyncio
async def test_openrouter_validate_key(httpx_mock):
    httpx_mock.add_response(url="https://openrouter.ai/api/v1/models", json={"data": [{"id": "anthropic/claude-3.5-sonnet"}]})
    provider = OpenRouterProvider(api_key="or-test")
    assert await provider.validate_key() is True
