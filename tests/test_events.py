import asyncio
import pytest
from backend.runner.events import EventEmitter
from backend.models import Event, EventType


@pytest.mark.asyncio
async def test_emit_and_subscribe():
    emitter = EventEmitter()
    received = []

    async def listener():
        async for event in emitter.subscribe():
            received.append(event)
            if len(received) >= 2:
                break

    task = asyncio.create_task(listener())
    await emitter.emit(Event(type=EventType.JOB_STATUS_CHANGE, job_id="j1", data={"status": "LOOPING"}))
    await emitter.emit(Event(type=EventType.JUDGE_SCORE, job_id="j1", data={"overall": 0.8}))
    await asyncio.wait_for(task, timeout=2.0)
    assert len(received) == 2
    assert received[0].type == EventType.JOB_STATUS_CHANGE


@pytest.mark.asyncio
async def test_subscribe_with_job_filter():
    emitter = EventEmitter()
    received = []

    async def listener():
        async for event in emitter.subscribe(job_id="j1"):
            received.append(event)
            if len(received) >= 1:
                break

    task = asyncio.create_task(listener())
    await emitter.emit(Event(type=EventType.ERROR, job_id="j2", data={}))
    await emitter.emit(Event(type=EventType.JUDGE_SCORE, job_id="j1", data={}))
    await asyncio.wait_for(task, timeout=2.0)
    assert len(received) == 1
    assert received[0].job_id == "j1"


@pytest.mark.asyncio
async def test_history():
    emitter = EventEmitter()
    await emitter.emit(Event(type=EventType.JOB_STATUS_CHANGE, job_id="j1", data={}))
    await emitter.emit(Event(type=EventType.JUDGE_SCORE, job_id="j1", data={}))
    assert len(emitter.history) == 2
