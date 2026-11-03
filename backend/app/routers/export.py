"""Export endpoints — PDF / Markdown / TXT downloads."""
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse

from backend.app import job_store
from backend.app.services.exporter import export_markdown, export_pdf, export_txt

router = APIRouter(prefix="/api/export", tags=["export"])


def _get_result(job_id: str) -> dict:
    job = job_store.store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.result:
        raise HTTPException(status_code=409, detail="Job has no results yet")
    return job.result


def _slug(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s[:60] or "meeting"


@router.get("/{job_id}/pdf")
def pdf(job_id: str):
    result = _get_result(job_id)
    buf = export_pdf(result)
    filename = f"{_slug(result.get('title', 'meeting'))}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{job_id}/markdown", response_class=PlainTextResponse)
def markdown(job_id: str):
    result = _get_result(job_id)
    return export_markdown(result)


@router.get("/{job_id}/txt", response_class=PlainTextResponse)
def txt(job_id: str):
    result = _get_result(job_id)
    return export_txt(result)
