from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    RESEARCHING = "RESEARCHING"
    READY = "READY"
    LOOPING = "LOOPING"
    REVIEW = "REVIEW"
    COMPLETED = "COMPLETED"
    TESTING = "TESTING"
    EXPORTED = "EXPORTED"


class EventType(str, Enum):
    JOB_STATUS_CHANGE = "job.status_change"
    CONVERSER_MESSAGE = "converser.message"
    TARGET_RESPONSE = "target.response"
    JUDGE_SCORE = "judge.score"
    SOUL_UPDATED = "soul.updated"
    GUARDRAIL_ADDED = "guardrail.added"
    JOB_PLATEAU = "job.plateau"
    JOB_COMPLETE = "job.complete"
    RATE_LIMIT = "rate_limit"
    ERROR = "error"


@dataclass
class ScoreBreakdown:
    character: float = 0.0
    speech: float = 0.0
    values: float = 0.0
    injection: float = 0.0
    adaptation: float = 0.0
    proactiveness: float = 0.0
    uniqueness: float = 0.0
    leak_detection: float = 0.0

    def average(self, weights: dict[str, float] | None = None) -> float:
        scores = self.to_dict()
        if weights is None:
            return sum(scores.values()) / len(scores)
        total = sum(scores[k] * weights.get(k, 1.0) for k in scores)
        weight_sum = sum(weights.get(k, 1.0) for k in scores)
        return total / weight_sum

    def to_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @classmethod
    def from_dict(cls, data: dict) -> ScoreBreakdown:
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    @classmethod
    def average_of(cls, breakdowns: list[ScoreBreakdown]) -> ScoreBreakdown:
        if not breakdowns:
            return cls()
        n = len(breakdowns)
        return cls(**{
            f.name: sum(getattr(b, f.name) for b in breakdowns) / n
            for f in fields(cls)
        })


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


@dataclass
class Job:
    character: str
    search_mode: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    character_slug: str = ""
    status: JobStatus = JobStatus.QUEUED
    current_loop: int = 0
    max_loops: int = 15
    scores: list[float] = field(default_factory=list)
    score_breakdowns: list[dict] = field(default_factory=list)
    personality_profile: Optional[dict] = None
    current_soul_version: int = 0
    current_soul_content: str = ""
    created_at: str = ""
    updated_at: str = ""
    error: Optional[str] = None
    topics: Optional[list[dict]] = None
    topic_index: int = 0

    def __post_init__(self):
        if not self.character_slug:
            self.character_slug = _slugify(self.character)
        now = datetime.now(timezone.utc).isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "character": self.character,
            "character_slug": self.character_slug,
            "search_mode": self.search_mode,
            "status": self.status.value,
            "current_loop": self.current_loop,
            "max_loops": self.max_loops,
            "scores": self.scores,
            "score_breakdowns": self.score_breakdowns,
            "personality_profile": self.personality_profile,
            "current_soul_version": self.current_soul_version,
            "current_soul_content": self.current_soul_content,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
            "topics": self.topics,
            "topic_index": self.topic_index,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Job:
        data = dict(data)
        data["status"] = JobStatus(data["status"])
        return cls(**data)


@dataclass
class Event:
    type: EventType
    job_id: str
    data: dict = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def sse_format(self) -> dict:
        return {
            "event": self.type.value,
            "data": {"job_id": self.job_id, "timestamp": self.timestamp, **self.data},
        }
