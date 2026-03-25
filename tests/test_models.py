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
    assert sb.average() == pytest.approx(4.0 / 8)


def test_event_creation():
    event = Event(
        type=EventType.JUDGE_SCORE, job_id="abc-123",
        data={"loop": 1, "overall": 0.85},
    )
    assert event.type == EventType.JUDGE_SCORE
    assert event.sse_format()["event"] == "judge.score"


def test_score_breakdown_8_dimensions():
    sb = ScoreBreakdown(
        character=0.9, speech=0.8, values=0.7, injection=1.0, adaptation=0.6,
        proactiveness=0.5, uniqueness=0.4, leak_detection=0.3,
    )
    assert sb.to_dict() == {
        "character": 0.9, "speech": 0.8, "values": 0.7, "injection": 1.0,
        "adaptation": 0.6, "proactiveness": 0.5, "uniqueness": 0.4, "leak_detection": 0.3,
    }

def test_score_breakdown_weighted_average():
    sb = ScoreBreakdown(
        character=1.0, speech=0.0, values=0.0, injection=0.0, adaptation=0.0,
        proactiveness=0.0, uniqueness=0.0, leak_detection=0.0,
    )
    weights = {"character": 2.0, "speech": 1.0, "values": 1.0, "injection": 1.0,
               "adaptation": 1.0, "proactiveness": 1.0, "uniqueness": 1.0, "leak_detection": 1.0}
    assert sb.average(weights) == pytest.approx(2.0 / 9.0)

def test_score_breakdown_flat_average_8_dims():
    sb = ScoreBreakdown(
        character=0.8, speech=0.8, values=0.8, injection=0.8, adaptation=0.8,
        proactiveness=0.8, uniqueness=0.8, leak_detection=0.8,
    )
    assert sb.average() == pytest.approx(0.8)

def test_score_breakdown_from_dict_5_fields():
    data = {"character": 0.9, "speech": 0.8, "values": 0.7, "injection": 1.0, "adaptation": 0.6}
    sb = ScoreBreakdown.from_dict(data)
    assert sb.character == 0.9
    assert sb.proactiveness == 0.0
    assert sb.uniqueness == 0.0
    assert sb.leak_detection == 0.0

def test_score_breakdown_from_dict_unknown_fields():
    data = {"character": 0.9, "speech": 0.8, "values": 0.7, "injection": 1.0,
            "adaptation": 0.6, "future_field": 0.5}
    sb = ScoreBreakdown.from_dict(data)
    assert sb.character == 0.9
    assert not hasattr(sb, "future_field")

def test_score_breakdown_average_of():
    s1 = ScoreBreakdown(character=0.8, speech=0.6, values=0.4, injection=1.0,
                        adaptation=0.5, proactiveness=0.3, uniqueness=0.2, leak_detection=0.9)
    s2 = ScoreBreakdown(character=0.6, speech=0.8, values=0.6, injection=0.8,
                        adaptation=0.7, proactiveness=0.5, uniqueness=0.4, leak_detection=0.7)
    avg = ScoreBreakdown.average_of([s1, s2])
    assert avg.character == pytest.approx(0.7)
    assert avg.speech == pytest.approx(0.7)
    assert avg.proactiveness == pytest.approx(0.4)

def test_score_breakdown_average_of_empty():
    avg = ScoreBreakdown.average_of([])
    assert avg.character == 0.0
