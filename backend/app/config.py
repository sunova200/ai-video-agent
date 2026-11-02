"""Application configuration via environment variables (pydantic-settings)."""
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── API keys ────────────────────────────────────────────────────────────
    mistral_api_key: str = ""
    sarvam_api_key: str = ""

    # ── Models ──────────────────────────────────────────────────────────────
    whisper_model: str = "small"
    mistral_model: str = "mistral-small-latest"
    embedding_model: str = "all-MiniLM-L6-v2"

    # ── Storage ─────────────────────────────────────────────────────────────
    chroma_dir: str = "vector_db"
    download_dir: str = "downloads"
    chunk_minutes: int = 10

    # ── Server ──────────────────────────────────────────────────────────────
    cors_origins: str = "*"          # comma-separated list, e.g. "http://localhost:5173,https://app.example.com"
    max_upload_mb: int = 500

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
