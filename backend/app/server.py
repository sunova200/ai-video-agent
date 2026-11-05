"""FastAPI application entry point.

Run (dev):      uvicorn backend.app.server:app --reload --port 8000
Run (prod):     gunicorn backend.app.server:app -k uvicorn.workers.UvicornWorker
Serve built frontend statically: set SERVE_FRONTEND=1 and run from repo root.
"""
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.config import get_settings
from backend.app.job_store import store
from backend.app.routers import chat, export, jobs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("server")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    store.load_all()
    logger.info("Restored %d job(s) from disk", len(store.list_jobs()))
    yield


app = FastAPI(
    title="AI Video Assistant API",
    description="Transcribe · Summarise · Chat with your meetings",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(chat.router)
app.include_router(export.router)


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok"}


# ── Optionally serve the built React frontend (single-container deploy) ────────
_frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.environ.get("SERVE_FRONTEND") == "1" and os.path.isdir(_frontend_dist):
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
    logger.info("Serving frontend from %s", _frontend_dist)
