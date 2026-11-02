"""RAG chat endpoint — ask questions about a completed meeting."""
from fastapi import APIRouter, HTTPException

from backend.app.job_store import store
from backend.app.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _build_chain_from_disk(job):
    """After a server restart the live chain is gone — rebuild it from the
    persisted Chroma vector store (cheap: no re-embedding needed)."""
    from core.rag_engine import load_rag_chain

    chain = load_rag_chain()
    store.attach_chain(job.id, chain)
    return chain


@router.post("/{job_id}", response_model=ChatResponse)
def chat(job_id: str, req: ChatRequest):
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status.value != "completed":
        raise HTTPException(status_code=409, detail=f"Job is {job.status.value}; chat available after completion")

    chain = store.get_chain(job_id)
    if chain is None:
        try:
            chain = _build_chain_from_disk(job)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"Could not restore RAG engine: {exc}") from exc

    try:
        answer = chain.invoke(req.question.strip())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}") from exc

    store.add_chat_message(job_id, "user", req.question.strip())
    store.add_chat_message(job_id, "assistant", answer)
    return ChatResponse(answer=answer)


@router.get("/{job_id}/history", response_model=list[dict])
def history(job_id: str):
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.chat_history
