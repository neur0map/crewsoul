import pytest
from pathlib import Path
from backend.runner.queue import JobQueue
from backend.models import Job, JobStatus


def test_add_job():
    q = JobQueue()
    job = q.add("Master Yoda", "normal")
    assert job.character == "Master Yoda"
    assert job.status == JobStatus.QUEUED
    assert len(q.all_jobs()) == 1


def test_get_job():
    q = JobQueue()
    job = q.add("Yoda", "normal")
    found = q.get(job.id)
    assert found is not None
    assert found.id == job.id


def test_get_nonexistent():
    q = JobQueue()
    assert q.get("fake-id") is None


def test_next_queued():
    q = JobQueue()
    q.add("Yoda", "normal")
    j2 = q.add("Obi-Wan", "smart")
    q.jobs[0].status = JobStatus.RESEARCHING
    queued = q.next_queued()
    assert queued is not None
    assert queued.character == "Obi-Wan"


def test_next_ready():
    q = JobQueue()
    j = q.add("Yoda", "normal")
    j.status = JobStatus.READY
    ready = q.next_ready()
    assert ready is not None
    assert ready.character == "Yoda"


def test_delete_job():
    q = JobQueue()
    j = q.add("Yoda", "normal")
    assert q.delete(j.id) is True
    assert len(q.all_jobs()) == 0


def test_delete_running_job_fails():
    q = JobQueue()
    j = q.add("Yoda", "normal")
    j.status = JobStatus.LOOPING
    assert q.delete(j.id) is False


def test_persist_and_rehydrate(tmp_output_dir: Path):
    q = JobQueue(output_dir=tmp_output_dir)
    j = q.add("Yoda", "normal")
    j.status = JobStatus.READY
    q.persist(j)

    q2 = JobQueue(output_dir=tmp_output_dir)
    q2.rehydrate()
    assert len(q2.all_jobs()) == 1
    assert q2.all_jobs()[0].status == JobStatus.READY
