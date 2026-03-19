from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from backend.models import Job, JobStatus

logger = logging.getLogger(__name__)


class JobQueue:
    def __init__(self, output_dir: Optional[Path] = None) -> None:
        self.jobs: list[Job] = []
        self.output_dir = output_dir

    def add(self, character: str, search_mode: str, max_loops: int = 15) -> Job:
        job = Job(character=character, search_mode=search_mode, max_loops=max_loops)
        self.jobs.append(job)
        logger.info("Job added: %s (%s)", character, job.id)
        return job

    def get(self, job_id: str) -> Optional[Job]:
        for job in self.jobs:
            if job.id == job_id:
                return job
        return None

    def all_jobs(self) -> list[Job]:
        return list(self.jobs)

    def next_queued(self) -> Optional[Job]:
        for job in self.jobs:
            if job.status == JobStatus.QUEUED:
                return job
        return None

    def next_ready(self) -> Optional[Job]:
        for job in self.jobs:
            if job.status == JobStatus.READY:
                return job
        return None

    def delete(self, job_id: str) -> bool:
        job = self.get(job_id)
        if job is None:
            return False
        if job.status in (JobStatus.LOOPING, JobStatus.RESEARCHING):
            return False
        self.jobs.remove(job)
        return True

    def persist(self, job: Job) -> None:
        if self.output_dir is None:
            return
        job_dir = self.output_dir / job.character_slug
        job_dir.mkdir(parents=True, exist_ok=True)
        state_path = job_dir / "job-state.json"
        state_path.write_text(json.dumps(job.to_dict(), indent=2))
        logger.info("Job persisted: %s → %s", job.id, state_path)

    def rehydrate(self) -> None:
        if self.output_dir is None or not self.output_dir.exists():
            return
        for job_dir in self.output_dir.iterdir():
            if not job_dir.is_dir():
                continue
            state_path = job_dir / "job-state.json"
            if not state_path.exists():
                continue
            data = json.loads(state_path.read_text())
            job = Job.from_dict(data)
            self.jobs.append(job)
            logger.info("Rehydrated job: %s (%s)", job.character, job.status.value)
