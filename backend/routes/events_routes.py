import json
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

router = APIRouter()


@router.get("/api/events")
async def event_stream(request: Request, job_id: str | None = None):
    emitter = request.app.state.emitter

    async def generate():
        async for event in emitter.subscribe(job_id=job_id):
            sse = event.sse_format()
            yield {"event": sse["event"], "data": json.dumps(sse["data"])}

    return EventSourceResponse(generate())
