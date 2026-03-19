from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timezone
from backend.agents.researcher import ResearcherAgent
from backend.agents.fetcher import FetcherAgent
from backend.models import Event, EventType, Job, JobStatus
from backend.output.writer import OutputWriter
from backend.providers.base import ProviderBase
from backend.runner.events import EventEmitter
from backend.runner.queue import JobQueue

logger = logging.getLogger(__name__)


class PreparationPipeline:
    def __init__(self, provider: ProviderBase, search, emitter: EventEmitter, queue: JobQueue, writer: OutputWriter, researcher_model: str, fetcher_model: str) -> None:
        self.provider = provider
        self.search = search
        self.researcher = ResearcherAgent(provider=provider, model=researcher_model, emitter=emitter, search=search)
        self.fetcher = FetcherAgent(provider=provider, model=fetcher_model, emitter=emitter, search=search)
        self.emitter = emitter
        self.queue = queue
        self.writer = writer

    async def prepare_job(self, job: Job) -> None:
        job.status = JobStatus.RESEARCHING
        job.updated_at = datetime.now(timezone.utc).isoformat()
        self.queue.persist(job)
        await self.emitter.emit(Event(type=EventType.JOB_STATUS_CHANGE, job_id=job.id, data={"status": job.status.value, "character": job.character}))
        try:
            profile, initial_soul = await self.researcher.research(job.character, job_id=job.id)
            job.personality_profile = profile
            job.current_soul_content = initial_soul
            job.current_soul_version = 0
            self.writer.write_profile(job, profile)
            self.writer.write_soul(job, initial_soul)
            topics = await self.fetcher.fetch_topics(job.character, job_id=job.id)
            job.topics = topics
            job.status = JobStatus.READY
            job.updated_at = datetime.now(timezone.utc).isoformat()
            self.queue.persist(job)
            await self.emitter.emit(Event(type=EventType.JOB_STATUS_CHANGE, job_id=job.id, data={"status": job.status.value}))
            logger.info("Job %s prepared: %d topics ready", job.id, len(topics))
        except Exception as e:
            job.error = str(e)
            job.status = JobStatus.REVIEW
            job.updated_at = datetime.now(timezone.utc).isoformat()
            self.queue.persist(job)
            await self.emitter.emit(Event(type=EventType.ERROR, job_id=job.id, data={"agent": "preparation", "message": str(e)}))
            logger.error("Preparation failed for %s: %s", job.character, e)

    async def run_continuous(self) -> None:
        while True:
            job = self.queue.next_queued()
            if job:
                await self.prepare_job(job)
            else:
                await asyncio.sleep(2.0)
