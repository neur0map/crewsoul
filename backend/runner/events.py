from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator, Optional

from backend.models import Event

logger = logging.getLogger(__name__)


class EventEmitter:
    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[Event]] = []
        self.history: list[Event] = []

    async def emit(self, event: Event) -> None:
        self.history.append(event)
        logger.info("Event: %s job=%s %s", event.type.value, event.job_id, json.dumps(event.data))
        await asyncio.sleep(0)  # yield to allow subscriber tasks to register
        for queue in self._subscribers:
            await queue.put(event)

    async def subscribe(self, job_id: Optional[str] = None) -> AsyncIterator[Event]:
        queue: asyncio.Queue[Event] = asyncio.Queue()
        self._subscribers.append(queue)
        try:
            while True:
                event = await queue.get()
                if job_id is None or event.job_id == job_id:
                    yield event
        finally:
            self._subscribers.remove(queue)
