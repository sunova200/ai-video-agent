"""Background pipeline runner — reuses the existing core/ + utils/ modules.

The heavy stages (audio download, Whisper transcription) run in a thread pool
so the FastAPI event loop stays responsive and many jobs can queue safely.
"""
import logging
import os
import sys
import traceback
from datetime import datetime, timezone

# Ensure project root is importable when running via `uvicorn backend.app.server`
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.app import job_store
from backend.app.schemas import JobStatus, StepState

logger = logging.getLogger("pipeline")


def _run_pipeline(job_id: str) -> None:
    from utils.audio_processor import process_input
    from core.transcriber import transcribe_all
    from core.summarizer import summarize, generate_title
    from core.extractor import extract_action_items, extract_key_decisions, extract_questions
    from core.rag_engine import build_rag_chain

    job = job_store.store.get(job_id)
    if not job:
        return
    job_store.store.update(job_id, status=JobStatus.running)

    def step(name):
        job_store.store.set_step(job_id, name, StepState.active.value)

    def done(name):
        job_store.store.set_step(job_id, name, StepState.done.value)

    try:
        step("audio")
        chunks = process_input(job.source)
        done("audio")

        step("transcript")
        transcript = transcribe_all(chunks, job.language)
        done("transcript")

        step("title")
        title = generate_title(transcript)
        done("title")

        step("summary")
        summary = summarize(transcript)
        done("summary")

        step("extract")
        action_items = extract_action_items(transcript)
        decisions = extract_key_decisions(transcript)
        questions = extract_questions(transcript)
        done("extract")

        step("rag")
        rag_chain = build_rag_chain(transcript)
        job_store.store.attach_chain(job_id, rag_chain)
        done("rag")

        job_store.store.update(
            job_id,
            status=JobStatus.completed,
            finished_at=datetime.now(timezone.utc),
            result={
                "title": title,
                "transcript": transcript,
                "summary": summary,
                "action_items": action_items,
                "key_decisions": decisions,
                "open_questions": questions,
            },
        )
        logger.info("Job %s completed", job_id)

    except Exception as exc:  # noqa: BLE001
        logger.error("Job %s failed: %s\n%s", job_id, exc, traceback.format_exc())
        # mark whichever step was active as failed
        j = job_store.store.get(job_id)
        if j:
            for k, v in dict(j.steps).items():
                if v == StepState.active.value:
                    job_store.store.set_step(job_id, k, StepState.failed.value)
        job_store.store.update(
            job_id,
            status=JobStatus.failed,
            error=str(exc)[:1000],
            finished_at=datetime.now(timezone.utc),
        )


def start_job(job_id: str) -> None:
    """Kick off the pipeline in a worker thread (fire-and-forget)."""
    import threading

    t = threading.Thread(target=_run_pipeline, args=(job_id,), daemon=True, name=f"pipeline-{job_id}")
    t.start()
