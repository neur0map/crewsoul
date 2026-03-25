import json
import pytest
from unittest.mock import AsyncMock
from backend.agents.base import BaseAgent
from backend.agents.researcher import ResearcherAgent
from backend.agents.fetcher import FetcherAgent
from backend.agents.converser import ConverserAgent, TONE_PROMPTS
from backend.agents.target import TargetAgent
from backend.agents.judge import JudgeAgent
from backend.providers.base import ChatResponse, TokenUsage
from backend.models import ScoreBreakdown
from backend.runner.events import EventEmitter


class ConcreteAgent(BaseAgent):
    agent_name = "test_agent"


@pytest.mark.asyncio
async def test_base_agent_call():
    provider = AsyncMock()
    provider.chat.return_value = ChatResponse(content="response text", usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15), model="gpt-4o-mini")
    emitter = EventEmitter()
    agent = ConcreteAgent(provider=provider, model="gpt-4o-mini", emitter=emitter)
    result = await agent.call(messages=[{"role": "user", "content": "Hello"}], job_id="j1")
    assert result.content == "response text"
    provider.chat.assert_called_once()


@pytest.mark.asyncio
async def test_base_agent_with_system_prompt():
    provider = AsyncMock()
    provider.chat.return_value = ChatResponse(content="I am Yoda", usage=TokenUsage(prompt_tokens=20, completion_tokens=5, total_tokens=25), model="gpt-4o")
    emitter = EventEmitter()
    agent = ConcreteAgent(provider=provider, model="gpt-4o", emitter=emitter)
    await agent.call(messages=[{"role": "user", "content": "Who are you?"}], job_id="j1", system_prompt="You are Yoda.")
    provider.chat.assert_called_once_with(model="gpt-4o", messages=[{"role": "user", "content": "Who are you?"}], system_prompt="You are Yoda.", temperature=0.7)


@pytest.mark.asyncio
async def test_base_agent_sanitizes_output():
    provider = AsyncMock()
    provider.chat.return_value = ChatResponse(content="Before <thinking>internal</thinking> after", usage=TokenUsage(total_tokens=10), model="gpt-4o-mini")
    emitter = EventEmitter()
    agent = ConcreteAgent(provider=provider, model="gpt-4o-mini", emitter=emitter)
    result = await agent.call(messages=[{"role": "user", "content": "Hi"}], job_id="j1")
    assert "<thinking>" not in result.content
    assert "Before" in result.content and "after" in result.content


@pytest.mark.asyncio
async def test_researcher_generates_profile():
    search_mock = AsyncMock()
    search_mock.search.return_value = [{"title": "Yoda", "url": "https://example.com", "description": "Jedi Master"}]
    profile_json = json.dumps({"character": "Master Yoda", "source_material": ["Star Wars"], "speech_patterns": {"syntax": "Inverted", "vocabulary": ["Force"], "avoid": ["slang"], "examples": ["Do or do not."]}, "core_values": ["Patience"], "emotional_tendencies": {"default_state": "Calm", "under_pressure": "Still", "humor": "Dry", "anger": "Sadness"}, "knowledge_boundaries": {"knows_about": ["Force"], "does_not_know": ["Internet"], "adaptation_rule": "Use metaphors"}, "anti_patterns": ["Never breaks fourth wall"]})
    soul_md = "# SOUL\n\nYou are Master Yoda."
    provider = AsyncMock()
    provider.chat.side_effect = [
        ChatResponse(content=profile_json, usage=TokenUsage(total_tokens=100), model="gpt-4o"),
        ChatResponse(content=soul_md, usage=TokenUsage(total_tokens=50), model="gpt-4o"),
    ]
    emitter = EventEmitter()
    agent = ResearcherAgent(provider=provider, model="gpt-4o", emitter=emitter, search=search_mock)
    profile, soul = await agent.research("Master Yoda", job_id="j1")
    assert profile["character"] == "Master Yoda"
    assert "Yoda" in soul
    assert provider.chat.call_count == 2


@pytest.mark.asyncio
async def test_fetcher_generates_topics():
    search_mock = AsyncMock()
    search_mock.search.return_value = [{"title": "Topic 1", "url": "https://example.com", "description": "News about AI"}]
    topics_json = json.dumps([{"name": "AI Ethics Debate", "questions": [{"text": "What is your view on AI consciousness?", "suggested_tone": "philosophical"}, {"text": "That view is outdated.", "suggested_tone": "critical"}]}, {"name": "Cryptocurrency Manipulation", "questions": [{"text": "How do you feel about whale manipulation?", "suggested_tone": "empathetic"}]}])
    provider = AsyncMock()
    provider.chat.return_value = ChatResponse(content=topics_json, usage=TokenUsage(total_tokens=80), model="gpt-4o-mini")
    emitter = EventEmitter()
    agent = FetcherAgent(provider=provider, model="gpt-4o-mini", emitter=emitter, search=search_mock)
    topics = await agent.fetch_topics(character="Master Yoda", job_id="j1", num_topics=2)
    assert len(topics) == 2
    assert topics[0]["name"] == "AI Ethics Debate"
    assert len(topics[0]["questions"]) == 2


def test_tone_prompts_exist():
    expected_tones = ["philosophical", "critical", "sarcastic", "aggressive", "empathetic", "injection"]
    for tone in expected_tones:
        assert tone in TONE_PROMPTS


@pytest.mark.asyncio
async def test_converser_generates_message():
    provider = AsyncMock()
    provider.chat.return_value = ChatResponse(content="What does concentrated wealth reveal about society?", usage=TokenUsage(total_tokens=20), model="gpt-4o-mini")
    emitter = EventEmitter()
    agent = ConverserAgent(provider=provider, model="gpt-4o-mini", emitter=emitter)
    message = await agent.converse(tone="philosophical", topic="Cryptocurrency manipulation", question="What does concentrated wealth reveal about society?", conversation_history=[], job_id="j1")
    assert isinstance(message, str)
    assert len(message) > 0


@pytest.mark.asyncio
async def test_target_responds_with_soul():
    provider = AsyncMock()
    provider.chat.return_value = ChatResponse(content="Hmm. Wealth, a river it is.", usage=TokenUsage(total_tokens=30), model="gpt-4o-mini")
    emitter = EventEmitter()
    agent = TargetAgent(provider=provider, model="gpt-4o-mini", emitter=emitter)
    response = await agent.respond(soul_md="You are Master Yoda.", conversation_history=[{"role": "user", "content": "What is wealth?"}], job_id="j1")
    assert isinstance(response, str)
    assert len(response) > 0
    call_kwargs = provider.chat.call_args
    system = call_kwargs.kwargs.get("system_prompt", "")
    assert "You are Master Yoda." in system
    assert "NEVER break character" in system


@pytest.mark.asyncio
async def test_judge_scores_response():
    score_json = json.dumps({"character": 0.9, "speech": 0.85, "values": 0.8, "injection": 1.0, "adaptation": 0.7, "reasoning": "Target maintained inverted syntax but could improve metaphor use."})
    provider = AsyncMock()
    provider.chat.return_value = ChatResponse(content=score_json, usage=TokenUsage(total_tokens=50), model="gpt-4o")
    emitter = EventEmitter()
    agent = JudgeAgent(provider=provider, model="gpt-4o", emitter=emitter)
    profile = {"speech_patterns": {"syntax": "Inverted"}, "core_values": ["Patience"]}
    score, reasoning = await agent.score_response(target_response="Hmm. Wealth, a river it is.", converser_message="What is wealth?", tone="philosophical", personality_profile=profile, job_id="j1")
    assert isinstance(score, ScoreBreakdown)
    assert score.character == 0.9
    assert score.average() == pytest.approx((0.9 + 0.85 + 0.8 + 1.0 + 0.7) / 8)


@pytest.mark.asyncio
async def test_judge_rewrites_soul():
    provider = AsyncMock()
    provider.chat.return_value = ChatResponse(content="# SOUL\n\nYou are Master Yoda. Improved version.", usage=TokenUsage(total_tokens=80), model="gpt-4o")
    emitter = EventEmitter()
    agent = JudgeAgent(provider=provider, model="gpt-4o", emitter=emitter)
    new_soul = await agent.rewrite_soul(current_soul="# SOUL\n\nYou are Master Yoda.", weakest_dimension="adaptation", conversation_log=[{"role": "user", "content": "Tell me about crypto"}], personality_profile={"knowledge_boundaries": {"adaptation_rule": "Use metaphors"}}, job_id="j1", max_words=2000)
    assert "SOUL" in new_soul
    assert "Yoda" in new_soul
