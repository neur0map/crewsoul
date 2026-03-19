import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.runner.preparation import PreparationPipeline
from backend.runner.events import EventEmitter
from backend.runner.queue import JobQueue
from backend.models import Job, JobStatus, EventType
from backend.providers.base import ChatResponse, TokenUsage


@pytest.fixture
def mock_pipeline(tmp_output_dir):
    provider = AsyncMock()
    search = AsyncMock()
    emitter = EventEmitter()
    queue = JobQueue(output_dir=tmp_output_dir)
    writer = MagicMock()
    return PreparationPipeline(
        provider=provider, search=search, emitter=emitter, queue=queue, writer=writer,
        researcher_model="gpt-4o", fetcher_model="gpt-4o-mini",
    )


@pytest.mark.asyncio
async def test_prepare_job(mock_pipeline):
    profile = {"character": "Yoda", "speech_patterns": {"syntax": "Inverted"}, "core_values": ["Patience"], "emotional_tendencies": {"default_state": "Calm"}, "knowledge_boundaries": {"knows_about": ["Force"]}, "anti_patterns": ["Never breaks character"]}
    topics = [{"name": "AI Ethics", "questions": [{"text": "What?", "suggested_tone": "philosophical"}]}]

    mock_pipeline.provider.chat.side_effect = [
        ChatResponse(content=json.dumps(profile), usage=TokenUsage(total_tokens=100), model="gpt-4o"),
        ChatResponse(content="# SOUL\nYou are Yoda.", usage=TokenUsage(total_tokens=50), model="gpt-4o"),
        ChatResponse(content=json.dumps(topics), usage=TokenUsage(total_tokens=80), model="gpt-4o-mini"),
    ]
    mock_pipeline.search.search.return_value = [{"title": "Yoda", "url": "", "description": "Jedi"}]

    job = mock_pipeline.queue.add("Yoda", "normal")
    await mock_pipeline.prepare_job(job)

    assert job.status == JobStatus.READY
    assert job.personality_profile is not None
    assert job.topics is not None
    assert len(job.topics) == 1
