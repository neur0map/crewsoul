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
