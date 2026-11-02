"""In-memory + on-disk job store.

Jobs live in memory for fast polling; their results are also persisted as JSON
under ``downloads/jobs/<job_id>.json`` so the app can restart without losing
history. Swap this module for Redis/Postgres when scaling horizontally.
"""
import json
import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from backend.app.config import get_settings
from backend.app.schemas import STEPS, JobStatus, StepInfo, StepState

_JOBS_DIRNAME = "jobs"


@dataclass
class Job:
    id: str
    source: str                 # url or uploaded file path
    source_type: str            # "url" | "upload"
    language: str
    status: JobStatus = JobStatus.queued
    progress: float = 0.0
    steps: dict[str, str] = field(default_factory=lambda: {s: StepState.pending.value for s in STEPS})
    result: Optional[dict] = None
    chat_history: list = field(default_factory=list)
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None


class JobStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._jobs: dict[str, Job] = {}
        self._rag_chains: dict[str, object] = {}   # live RAG chains (not serialisable)

    # ── directory helpers ───────────────────────────────────────────────────
    @property
    def _dir(self) -> str:
        d = os.path.join(get_settings().download_dir, _JOBS_DIRNAME)
        os.makedirs(d, exist_ok=True)
        return d

    def _path(self, job_id: str) -> str:
        return os.path.join(self._dir, f"{job_id}.json")

    # ── CRUD ────────────────────────────────────────────────────────────────
    def create(self, source: str, source_type: str, language: str) -> Job:
        job = Job(
            id=uuid.uuid4().hex[:12],
            source=source,
            source_type=source_type,
            language=language,
        )
        with self._lock:
            self._jobs[job.id] = job
            self._persist(job)
        return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            if job_id in self._jobs:
                return self._jobs[job_id]
        # fallback: load from disk (e.g. after server restart)
        path = self._path(job_id)
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                # rehydrate datetimes persisted as ISO strings
                if isinstance(data.get("created_at"), str):
                    data["created_at"] = datetime.fromisoformat(data["created_at"])
                if isinstance(data.get("finished_at"), str):
                    data["finished_at"] = datetime.fromisoformat(data["finished_at"])
                job = Job(**data)
                job.status = JobStatus(job.status)
                with self._lock:
                    self._jobs[job.id] = job
                return job
            except Exception:
                return None
        return None

    def list_jobs(self) -> list[Job]:
        with self._lock:
            jobs = list(self._jobs.values())
        # created_at may be a str on rehydrated jobs → normalise for sorting
        jobs.sort(key=lambda j: str(j.created_at), reverse=True)
        return jobs

    def update(self, job_id: str, **changes) -> Optional[Job]:
        with self._lock:
            job = self.get(job_id)
            if not job:
                return None
            for k, v in changes.items():
                setattr(job, k, v)
            self._persist(job)
            return job

    def set_step(self, job_id: str, step: str, state: str) -> None:
        with self._lock:
            job = self.get(job_id)
            if not job:
                return
            job.steps[step] = state
            # progress = fraction of completed steps
            done = sum(1 for s in job.steps.values() if s == StepState.done.value)
            job.progress = round(done / len(job.steps), 3)
            self._persist(job)

    # ── RAG chain cache (per-process) ──────────────────────────────────────
    def attach_chain(self, job_id: str, chain) -> None:
        with self._lock:
            self._rag_chains[job_id] = chain

    def get_chain(self, job_id: str):
        with self._lock:
            return self._rag_chains.get(job_id)

    def add_chat_message(self, job_id: str, role: str, content: str) -> None:
        with self._lock:
            job = self.get(job_id)
            if job:
                job.chat_history.append({"role": role, "content": content})
                self._persist(job)

    # ── serialisation ───────────────────────────────────────────────────────
    def _persist(self, job: Job) -> None:
        try:
            with open(self._path(job.id), "w", encoding="utf-8") as f:
                json.dump(job.__dict__, f, default=str, ensure_ascii=False)
        except Exception:
            pass  # never let persistence break the pipeline

    def load_all(self) -> None:
        """Rehydrate jobs from disk on startup."""
        d = self._dir
        if not os.path.isdir(d):
            return
        for name in os.listdir(d):
            if not name.endswith(".json"):
                continue
            try:
                with open(os.path.join(d, name), encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data.get("created_at"), str):
                    data["created_at"] = datetime.fromisoformat(data["created_at"])
                if isinstance(data.get("finished_at"), str):
                    data["finished_at"] = datetime.fromisoformat(data["finished_at"])
                job = Job(**data)
                job.status = JobStatus(job.status)
                # a job that was mid-flight when the server died → mark failed
                if job.status in (JobStatus.queued, JobStatus.running):
                    job.status = JobStatus.failed
                    job.error = "Server restarted while job was running."
                self._jobs[job.id] = job
            except Exception:
                continue


def step_infos(job: Job) -> list[StepInfo]:
    labels = {
        "audio": "Audio Processing",
        "transcript": "Transcription",
        "title": "Title Generation",
        "summary": "Summarisation",
        "extract": "Extraction",
        "rag": "RAG Engine",
    }
    return [StepInfo(name=s, label=labels[s], state=StepState(job.steps[s])) for s in STEPS]


store = JobStore()
