"""Job endpoints — create analysis jobs, poll status, upload files."""
import os
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from backend.app.config import get_settings
from backend.app import job_store
from backend.app.job_store import step_infos
from backend.app.pipeline import start_job
from backend.app.schemas import (
    AnalyzeURLRequest,
    JobDetail,
    JobStatus,
    JobSummary,
    MeetingResult,
)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _to_detail(job) -> JobDetail:
    return JobDetail(
        job_id=job.id,
        status=JobStatus(job.status),
        source=job.source,
        language=job.language,
        created_at=job.created_at,
        finished_at=job.finished_at,
        progress=job.progress,
        steps=step_infos(job),
        error=job.error,
        result=MeetingResult(**job.result) if job.result else None,
    )


@router.post("/analyze-url", response_model=JobSummary, status_code=status.HTTP_202_ACCEPTED)
def analyze_url(req: AnalyzeURLRequest):
    """Start an analysis job from a YouTube (yt-dlp supported) URL."""
    job = job_store.store.create(source=req.url.strip(), source_type="url", language=req.language.value)
    start_job(job.id)
    return JobSummary(
        job_id=job.id, status=job.status, source=job.source,
        language=job.language, created_at=job.created_at,
    )


@router.post("/upload", response_model=JobSummary, status_code=status.HTTP_202_ACCEPTED)
async def upload_and_analyze(
    file: UploadFile = File(...),
    language: str = Form("english"),
):
    """Upload an audio/video file, then start an analysis job."""
    settings = get_settings()
    if language not in ("english", "hinglish"):
        raise HTTPException(status_code=422, detail="language must be 'english' or 'hinglish'")

    ext = os.path.splitext(file.filename or "")[1] or ".bin"
    safe_name = f"{uuid.uuid4().hex[:8]}{ext}"
    dest_dir = os.path.join(settings.download_dir, "uploads")
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, safe_name)

    # stream to disk in 1 MB blocks (memory-friendly for large files)
    size = 0
    max_bytes = settings.max_upload_mb * 1024 * 1024
    with open(dest, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                out.close()
                os.remove(dest)
                raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb} MB limit")
            out.write(chunk)

    job = job_store.store.create(source=dest, source_type="upload", language=language)
    start_job(job.id)
    return JobSummary(
        job_id=job.id, status=job.status, source=file.filename or safe_name,
        language=job.language, created_at=job.created_at,
    )


@router.get("", response_model=list[JobSummary])
def list_jobs():
    return [
        JobSummary(
            job_id=j.id, status=JobStatus(j.status), source=j.source,
            language=j.language, created_at=j.created_at, finished_at=j.finished_at,
        )
        for j in job_store.store.list_jobs()
    ]


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: str):
    """Poll job status / progress / results."""
    job = job_store.store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _to_detail(job)
