import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.runner.orchestrator import Orchestrator
from backend.runner.events import EventEmitter
from backend.runner.queue import JobQueue
from backend.models import Job, JobStatus, ScoreBreakdown
from backend.providers.base import ChatResponse, TokenUsage


@pytest.fixture
def mock_orchestrator(tmp_output_dir):
    provider = AsyncMock()
    emitter = EventEmitter()
    queue = JobQueue(output_dir=tmp_output_dir)
    writer = MagicMock()
    orch = Orchestrator(
        provider=provider, emitter=emitter, queue=queue, writer=writer,
        converser_model="gpt-4o-mini", target_model="gpt-4o-mini", judge_model="gpt-4o",
        config=MagicMock(questions_per_loop=2, tone_rotation="per_question", score_threshold=0.9, max_loops=15, plateau_window=3, soul_max_words=2000),
    )
    return orch, provider, queue


def _make_loop_responses(score_json: str) -> list:
    """Create mock responses for one loop: 2 questions × (converser + target + judge) + 1 rewrite = 7 calls."""
    return [
        ChatResponse(content="What about AI consciousness?", usage=TokenUsage(total_tokens=20), model="m"),
        ChatResponse(content="Hmm. Conscious, machines may become.", usage=TokenUsage(total_tokens=20), model="m"),
        ChatResponse(content=score_json, usage=TokenUsage(total_tokens=20), model="m"),
        ChatResponse(content="That's wrong.", usage=TokenUsage(total_tokens=20), model="m"),
        ChatResponse(content="Wrong, I think not.", usage=TokenUsage(total_tokens=20), model="m"),
        ChatResponse(content=score_json, usage=TokenUsage(total_tokens=20), model="m"),
        # rewrite_soul call (always happens now)
        ChatResponse(content="# SOUL\nYou are Yoda. Improved.", usage=TokenUsage(total_tokens=40), model="m"),
    ]


@pytest.mark.asyncio
async def test_run_single_loop_continues_under_minimum(mock_orchestrator):
    """A single high-scoring loop should NOT complete — minimum 3 loops required."""
    orch, provider, queue = mock_orchestrator
    job = queue.add("Yoda", "normal")
    job.status = JobStatus.READY
    job.personality_profile = {"speech_patterns": {"syntax": "Inverted"}}
    job.current_soul_content = "# SOUL\nYou are Yoda."
    job.topics = [
        {"name": "AI Ethics", "questions": [{"text": "What about AI?", "suggested_tone": "philosophical"}, {"text": "You're wrong.", "suggested_tone": "critical"}]},
        {"name": "Topic 2", "questions": [{"text": "Q1", "suggested_tone": "sarcastic"}, {"text": "Q2", "suggested_tone": "aggressive"}]},
        {"name": "Topic 3", "questions": [{"text": "Q3", "suggested_tone": "empathetic"}, {"text": "Q4", "suggested_tone": "injection"}]},
    ]

    score_json = json.dumps({"character": 0.95, "speech": 0.9, "values": 0.85, "injection": 1.0, "adaptation": 0.95, "reasoning": "Good."})
    provider.chat.side_effect = _make_loop_responses(score_json)

    completed = await orch.run_loop(job)
    assert completed is False  # Must not complete — under minimum loops
    assert len(job.scores) == 1
    assert job.scores[0] >= 0.9
    assert job.current_soul_version == 1  # SOUL was rewritten


@pytest.mark.asyncio
async def test_completes_after_minimum_loops(mock_orchestrator):
    """Job should complete when score >= threshold AND past minimum loops."""
    orch, provider, queue = mock_orchestrator
    job = queue.add("Yoda", "normal")
    job.status = JobStatus.LOOPING
    job.current_loop = 2  # Already ran 2 loops
    job.scores = [0.85, 0.90]
    job.personality_profile = {"speech_patterns": {"syntax": "Inverted"}}
    job.current_soul_content = "# SOUL\nYou are Yoda."
    job.topics = [
        {"name": "T1", "questions": []},
        {"name": "T2", "questions": []},
        {"name": "Topic 3", "questions": [{"text": "Q1", "suggested_tone": "philosophical"}, {"text": "Q2", "suggested_tone": "critical"}]},
    ]
    job.topic_index = 2

    score_json = json.dumps({"character": 0.95, "speech": 0.92, "values": 0.90, "injection": 1.0, "adaptation": 0.93, "reasoning": "Excellent."})
    provider.chat.side_effect = _make_loop_responses(score_json)

    completed = await orch.run_loop(job)
    assert completed is True
    assert job.status == JobStatus.COMPLETED
    assert len(job.scores) == 3


def test_plateau_detection(mock_orchestrator):
    orch, provider, queue = mock_orchestrator
    orch.config.plateau_window = 2
    job = queue.add("Yoda", "normal")
    job.scores = [0.7, 0.7]
    assert orch._check_plateau(job) is True


def test_no_plateau_with_improvement(mock_orchestrator):
    orch, provider, queue = mock_orchestrator
    orch.config.plateau_window = 3
    job = queue.add("Yoda", "normal")
    job.scores = [0.6, 0.7, 0.75]
    assert orch._check_plateau(job) is False
