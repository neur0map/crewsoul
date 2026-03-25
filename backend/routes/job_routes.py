import io
import json
import zipfile
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from backend.models import JobStatus

router = APIRouter(prefix="/api/jobs")


@router.post("")
async def create_job(request: Request):
    data = await request.json()
    character = data.get("character", "")
    search_mode = data.get("search_mode", "normal")
    if not character:
        return JSONResponse(status_code=400, content={"error": "character is required"})
    queue = request.app.state.queue
    config = request.app.state.config
    max_loops = config.orchestration.max_loops if config else 15
    job = queue.add(character, search_mode, max_loops=max_loops)
    return job.to_dict()


@router.get("")
async def list_jobs(request: Request):
    return [j.to_dict() for j in request.app.state.queue.all_jobs()]


@router.get("/{job_id}")
async def get_job(request: Request, job_id: str):
    job = request.app.state.queue.get(job_id)
    if job is None:
        return JSONResponse(status_code=404, content={"error": "Job not found"})
    return job.to_dict()


@router.delete("/{job_id}")
async def delete_job(request: Request, job_id: str):
    if request.app.state.queue.delete(job_id):
        return {"status": "deleted"}
    return JSONResponse(status_code=400, content={"error": "Cannot delete running job"})


@router.patch("/{job_id}")
async def update_job(request: Request, job_id: str):
    job = request.app.state.queue.get(job_id)
    if job is None:
        return JSONResponse(status_code=404, content={"error": "Job not found"})
    data = await request.json()
    if "search_mode" in data:
        job.search_mode = data["search_mode"]
    request.app.state.queue.persist(job)
    return job.to_dict()


VALID_WEIGHT_KEYS = {"character", "speech", "values", "injection", "adaptation",
                     "proactiveness", "uniqueness", "leak_detection"}

@router.patch("/{job_id}/profile")
async def update_profile(request: Request, job_id: str):
    job = request.app.state.queue.get(job_id)
    if job is None:
        return JSONResponse(status_code=404, content={"error": "Job not found"})
    if job.status != JobStatus.READY:
        return JSONResponse(status_code=400, content={"error": f"Can only edit profile in READY state, got {job.status.value}"})
    if job.personality_profile is None:
        return JSONResponse(status_code=400, content={"error": "No personality profile exists yet"})
    data = await request.json()
    if "reference_samples" in data:
        samples = data["reference_samples"]
        if not isinstance(samples, list) or not all(isinstance(s, str) and s.strip() for s in samples):
            return JSONResponse(status_code=400, content={"error": "reference_samples must be a list of non-empty strings"})
        job.personality_profile["reference_samples"] = samples
    if "score_weights" in data:
        weights = data["score_weights"]
        if not isinstance(weights, dict):
            return JSONResponse(status_code=400, content={"error": "score_weights must be a dict"})
        invalid_keys = set(weights.keys()) - VALID_WEIGHT_KEYS
        if invalid_keys:
            return JSONResponse(status_code=400, content={"error": f"Invalid weight keys: {invalid_keys}"})
        existing = job.personality_profile.get("score_weights", {})
        existing.update(weights)
        job.personality_profile["score_weights"] = existing
    request.app.state.queue.persist(job)
    return job.to_dict()


@router.post("/{job_id}/approve")
async def approve_job(request: Request, job_id: str):
    job = request.app.state.queue.get(job_id)
    if job is None:
        return JSONResponse(status_code=404, content={"error": "Job not found"})
    if job.status not in (JobStatus.REVIEW, JobStatus.COMPLETED):
        return JSONResponse(status_code=400, content={"error": f"Cannot approve job in {job.status.value} state"})
    job.status = JobStatus.TESTING
    request.app.state.queue.persist(job)
    return job.to_dict()


@router.post("/{job_id}/resume")
async def resume_job(request: Request, job_id: str):
    job = request.app.state.queue.get(job_id)
    if job is None:
        return JSONResponse(status_code=404, content={"error": "Job not found"})
    if job.status != JobStatus.REVIEW:
        return JSONResponse(status_code=400, content={"error": "Can only resume REVIEW jobs"})
    job.status = JobStatus.READY
    request.app.state.queue.persist(job)
    return job.to_dict()


@router.post("/{job_id}/export")
async def export_job(request: Request, job_id: str):
    job = request.app.state.queue.get(job_id)
    if job is None:
        return JSONResponse(status_code=404, content={"error": "Job not found"})
    job.status = JobStatus.EXPORTED
    request.app.state.queue.persist(job)
    return job.to_dict()


@router.get("/{job_id}/soul")
async def get_soul(request: Request, job_id: str):
    job = request.app.state.queue.get(job_id)
    if job is None:
        return JSONResponse(status_code=404, content={"error": "Job not found"})
    return {"content": job.current_soul_content, "version": job.current_soul_version}


@router.get("/{job_id}/diff")
async def get_diff(request: Request, job_id: str):
    job = request.app.state.queue.get(job_id)
    if job is None:
        return JSONResponse(status_code=404, content={"error": "Job not found"})
    log_path = request.app.state.output_dir / job.character_slug / "evolution-log.json"
    if not log_path.exists():
        return {"entries": []}
    return {"entries": json.loads(log_path.read_text())}


@router.get("/{job_id}/logs")
async def get_logs(request: Request, job_id: str):
    job = request.app.state.queue.get(job_id)
    if job is None:
        return JSONResponse(status_code=404, content={"error": "Job not found"})
    log_path = request.app.state.output_dir / job.character_slug / "evolution-log.json"
    if not log_path.exists():
        return {"entries": []}
    return {"entries": json.loads(log_path.read_text())}


@router.get("/{job_id}/artifacts")
async def get_artifacts(request: Request, job_id: str):
    job = request.app.state.queue.get(job_id)
    if job is None:
        return JSONResponse(status_code=404, content={"error": "Job not found"})
    job_dir = request.app.state.output_dir / job.character_slug
    if not job_dir.exists():
        return JSONResponse(status_code=404, content={"error": "No artifacts found"})
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in job_dir.rglob("*"):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(job_dir))
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={job.character_slug}-artifacts.zip"},
    )
