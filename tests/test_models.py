import pytest
from backend.models import Job, JobStatus, Event, EventType, ScoreBreakdown


def test_job_creation():
    job = Job(character="Master Yoda", search_mode="normal")
    assert job.status == JobStatus.QUEUED
    assert job.character_slug == "master-yoda"
    assert job.current_loop == 0
    assert job.scores == []
    assert job.id


def test_job_slug_generation():
    job = Job(character="Obi-Wan Kenobi", search_mode="smart")
    assert job.character_slug == "obi-wan-kenobi"


def test_job_serialization():
    job = Job(character="Master Yoda", search_mode="normal")
    data = job.to_dict()
    restored = Job.from_dict(data)
    assert restored.character == "Master Yoda"
    assert restored.id == job.id


def test_score_breakdown():
    sb = ScoreBreakdown(
        character=0.9, speech=0.8, values=0.7, injection=1.0, adaptation=0.6,
    )
    assert sb.average() == pytest.approx(0.8)


def test_event_creation():
    event = Event(
        type=EventType.JUDGE_SCORE, job_id="abc-123",
        data={"loop": 1, "overall": 0.85},
    )
    assert event.type == EventType.JUDGE_SCORE
    assert event.sse_format()["event"] == "judge.score"
