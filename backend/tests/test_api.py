"""API tests — run with: pytest backend/tests -q

Heavy ML deps (whisper, torch, langchain) are NOT required; the pipeline is
mocked via sys.modules injection. The pipeline thread is *synchronous*, so we
join it before asserting — no flaky polling.
"""
import io
import os
import sys
import threading
import types

# ── make project root importable ──────────────────────────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest
from fastapi.testclient import TestClient

# ── stub out heavy modules BEFORE importing the server ────────────────────────
def _stub(name: str, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


class _FakeChain:
    def invoke(self, q):
        return f"Mock answer for: {q}"


_stub("utils.audio_processor", process_input=lambda src: ["fake_chunk.wav"])
_stub("core.transcriber", transcribe_all=lambda chunks, lang="english": "This is a mock transcript about a planning meeting.")
_stub("core.summarizer", summarize=lambda t: "- Mock summary bullet", generate_title=lambda t: "Mock Meeting Title")
_stub("core.extractor",
      extract_action_items=lambda t: "1. Do the thing",
      extract_key_decisions=lambda t: "1. Chose X",
      extract_questions=lambda t: "1. When?")
_stub("core.rag_engine", build_rag_chain=lambda t: _FakeChain(), load_rag_chain=lambda: _FakeChain())
_stub("core.vector_store")
_stub("fpdf", FPDF=object)  # PDF export tested structurally only

# deterministic job execution: keep references to threads and join on demand
_THREADS: list[threading.Thread] = []
_real_start = None


def _tracked_start_job(job_id: str) -> None:
    from backend.app import pipeline as pl

    t = threading.Thread(target=pl._run_pipeline, args=(job_id,), name=f"pipeline-{job_id}")
    _THREADS.append(t)
    t.start()


import backend.app.pipeline as _pl  # noqa: E402

_pl.start_job = _tracked_start_job  # patch before routers capture the reference

from backend.app.server import app  # noqa: E402


def _drain():
    """Wait for all spawned fake-pipeline threads to finish."""
    for t in list(_THREADS):
        t.join(timeout=10)
    _THREADS.clear()


@pytest.fixture()
def client(request, tmp_path, monkeypatch):
    monkeypatch.setattr("backend.app.config.get_settings", lambda: _settings(tmp_path))
    # routers/pipeline call get_settings imported into their own namespaces
    import backend.app.routers.jobs as jobs_mod
    monkeypatch.setattr(jobs_mod, "get_settings", lambda: _settings(tmp_path))

    fresh_store = request.node.get_closest_marker("fresh_store") is not None
    if fresh_store:
        from backend.app import job_store
        import backend.app.pipeline as pl
        import backend.app.routers.chat as chat_mod
        import backend.app.routers.export as export_mod

        replacement = job_store.JobStore()
        # monkeypatch restores the originals at teardown automatically
        monkeypatch.setattr(job_store, "store", replacement)
        monkeypatch.setattr(pl, "store", replacement)
        monkeypatch.setattr(chat_mod, "store", replacement)
        monkeypatch.setattr(export_mod, "store", replacement)
    with TestClient(app) as c:
        yield c


_SETTINGS_CACHE = {}


def _settings(tmp_path):
    key = str(tmp_path)
    if key not in _SETTINGS_CACHE:
        from backend.app.config import Settings
        _SETTINGS_CACHE[key] = Settings(download_dir=str(tmp_path / "dl"), max_upload_mb=500)
    return _SETTINGS_CACHE[key]


def _wait_done(client, job_id):
    """Join the fake pipeline threads, then fetch final detail."""
    _drain()
    r = client.get(f"/api/jobs/{job_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed", body
    return body


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_analyze_url_full_lifecycle(client):
    r = client.post("/api/jobs/analyze-url", json={"url": "https://youtube.com/watch?v=abc123", "language": "english"})
    assert r.status_code == 202
    job_id = r.json()["job_id"]

    detail = _wait_done(client, job_id)
    assert detail["status"] == "completed"
    assert detail["progress"] == 1.0
    res = detail["result"]
    assert res["title"] == "Mock Meeting Title"
    assert "Mock summary" in res["summary"]
    assert all(s["state"] == "done" for s in detail["steps"])

    # chat
    c = client.post(f"/api/chat/{job_id}", json={"question": "What was decided?"})
    assert c.status_code == 200
    assert "Mock answer" in c.json()["answer"]

    h = client.get(f"/api/chat/{job_id}/history")
    assert h.status_code == 200
    assert len(h.json()) == 2

    # exports
    assert client.get(f"/api/export/{job_id}/markdown").text.startswith("# Mock Meeting Title")
    assert "FULL TRANSCRIPT" in client.get(f"/api/export/{job_id}/txt").text
    md = client.get(f"/api/export/{job_id}/markdown")
    assert "## Action Items" in md.text


def test_upload_and_list(client):
    files = {"file": ("meeting.mp4", io.BytesIO(b"fake-bytes"), "video/mp4")}
    r = client.post("/api/jobs/upload", files=files, data={"language": "hinglish"})
    assert r.status_code == 202
    job_id = r.json()["job_id"]

    detail = _wait_done(client, job_id)
    assert detail["status"] == "completed"
    assert detail["language"] == "hinglish"

    lst = client.get("/api/jobs").json()
    assert any(j["job_id"] == job_id for j in lst)


def test_upload_too_large(client, monkeypatch):
    import backend.app.routers.jobs as jobs_mod

    s = jobs_mod.get_settings()
    monkeypatch.setattr(s, "max_upload_mb", 0)  # 0 MB → any upload fails
    files = {"file": ("big.mp4", io.BytesIO(b"x" * 1024), "video/mp4")}
    r = client.post("/api/jobs/upload", files=files)
    assert r.status_code == 413


def test_chat_before_completion_409(client, monkeypatch):
    """Chat must be rejected while the job is still running.

    We slow down the fake transcription step so the status is
    deterministically 'running' when we attempt to chat.
    """
    import time as _time
    import core.transcriber as transcriber_stub

    def slow_transcribe(chunks, lang="english"):
        _time.sleep(1.5)
        return "slow mock transcript"

    monkeypatch.setattr(transcriber_stub, "transcribe_all", slow_transcribe)

    r = client.post("/api/jobs/analyze-url", json={"url": "https://youtu.be/zzzzzzzz", "language": "english"})
    assert r.status_code == 202
    job_id = r.json()["job_id"]

    detail = client.get(f"/api/jobs/{job_id}").json()
    assert detail["status"] in ("queued", "running")

    c = client.post(f"/api/chat/{job_id}", json={"question": "hi"})
    assert c.status_code == 409

    _drain()  # let the background job finish before teardown


def test_job_not_found(client):
    assert client.get("/api/jobs/nonexistent").status_code == 404
    assert client.post("/api/chat/nonexistent", json={"question": "x"}).status_code == 404


def test_invalid_url_rejected(client):
    r = client.post("/api/jobs/analyze-url", json={"url": "short", "language": "english"})
    assert r.status_code == 422
