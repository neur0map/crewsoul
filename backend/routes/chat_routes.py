import json
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from backend.models import JobStatus
from backend.sanitizer import sanitize_llm_output

router = APIRouter(prefix="/api/chat")
_chat_histories: dict[str, list[dict]] = {}


@router.post("/{job_id}")
async def send_message(request: Request, job_id: str):
    queue = request.app.state.queue
    job = queue.get(job_id)
    if job is None:
        return JSONResponse(status_code=404, content={"error": "Job not found"})
    if job.status not in (JobStatus.TESTING, JobStatus.COMPLETED, JobStatus.REVIEW):
        return JSONResponse(status_code=400, content={"error": f"Cannot chat with job in {job.status.value} state"})
    data = await request.json()
    user_message = data.get("message", "")
    if not user_message:
        return JSONResponse(status_code=400, content={"error": "message is required"})
    if job_id not in _chat_histories:
        _chat_histories[job_id] = []
    _chat_histories[job_id].append({"role": "user", "content": user_message})
    provider = getattr(request.app.state, "chat_provider", None)
    if provider is None:
        return JSONResponse(status_code=500, content={"error": "No provider configured"})
    config = request.app.state.config
    target_model = config.provider.active_config().models.target if config else "gpt-4o-mini"
    response = await provider.chat(model=target_model, messages=_chat_histories[job_id], system_prompt=job.current_soul_content)
    clean_content = sanitize_llm_output(response.content)
    _chat_histories[job_id].append({"role": "assistant", "content": clean_content})
    output_dir = request.app.state.output_dir
    chat_path = output_dir / job.character_slug / "test-chat.json"
    chat_path.parent.mkdir(parents=True, exist_ok=True)
    chat_path.write_text(json.dumps(_chat_histories[job_id], indent=2))
    return {"response": clean_content, "history": _chat_histories[job_id]}


@router.get("/{job_id}")
async def get_chat_history(request: Request, job_id: str):
    return {"history": _chat_histories.get(job_id, [])}
