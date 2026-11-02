"""Pydantic request/response schemas for the API."""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Language(str, Enum):
    english = "english"
    hinglish = "hinglish"


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class StepState(str, Enum):
    pending = "pending"
    active = "active"
    done = "done"
    failed = "failed"


# ── Requests ────────────────────────────────────────────────────────────────────
class AnalyzeURLRequest(BaseModel):
    url: str = Field(..., min_length=8, description="YouTube (or yt-dlp supported) URL")
    language: Language = Language.english


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


# ── Pipeline steps ──────────────────────────────────────────────────────────────
STEPS = ["audio", "transcript", "title", "summary", "extract", "rag"]


class StepInfo(BaseModel):
    name: str
    label: str
    state: StepState = StepState.pending


# ── Responses ───────────────────────────────────────────────────────────────────
class JobSummary(BaseModel):
    job_id: str
    status: JobStatus
    source: str
    language: str
    created_at: datetime
    finished_at: Optional[datetime] = None


class JobDetail(JobSummary):
    progress: float = 0.0
    steps: list[StepInfo] = []
    error: Optional[str] = None
    result: Optional["MeetingResult"] = None


class MeetingResult(BaseModel):
    title: str = ""
    transcript: str = ""
    summary: str = ""
    action_items: str = ""
    key_decisions: str = ""
    open_questions: str = ""


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatResponse(BaseModel):
    answer: str


JobDetail.model_rebuild()
