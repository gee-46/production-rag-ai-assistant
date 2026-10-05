"""
Centralized application configuration.

Every tunable in the old codebase (model names, chunk size, top_k, DB path)
was a hardcoded literal inside the module that used it. That made the system
impossible to configure per-environment and impossible to unit test with
different parameters. Everything now flows through this single Settings
object, loaded once from environment variables / .env.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    app_name: str = "Production RAG Platform"
    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    log_json: bool = False

    # --- Security & Access Control ---
    auth_enabled: bool = False  # False for frictionless local demo; True enforces JWT auth
    demo_local_only: bool = True  # When auth is disabled, restrict unauthenticated demo access to localhost
    secret_key: str = Field(default="CHANGE_ME_INSECURE_DEV_KEY", min_length=8)
    access_token_expire_minutes: int = 60 * 24  # 24h
    jwt_algorithm: str = "HS256"


    # --- Database ---
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/ragdb"

    # --- Embeddings ---
    embedding_provider: Literal["sentence_transformers", "openai", "fake"] = "sentence_transformers"
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384  # must match embedding_model's output dimension

    # --- LLM ---
    llm_provider: Literal["groq", "openai", "anthropic", "ollama", "fake"] = "groq"
    llm_model: str = "llama-3.1-8b-instant"
    groq_api_key: str | None = None
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    llm_request_timeout_s: float = 30.0
    llm_max_retries: int = 2

    # --- Retrieval ---
    chunk_target_tokens: int = 300
    chunk_overlap_tokens: int = 50
    vector_top_k: int = 20
    keyword_top_k: int = 20
    rerank_top_k: int = 5
    hybrid_rrf_k: int = 60  # reciprocal-rank-fusion constant
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker_provider: Literal["cross_encoder", "fake"] = "cross_encoder"

    # --- Uploads ---
    max_upload_mb: int = 25
    upload_dir: str = "./data/uploads"
    allowed_upload_extensions: tuple[str, ...] = (".txt", ".md", ".docx", ".pdf")

    # --- Jobs ---
    job_poll_interval_s: float = 1.0

    @field_validator("database_url")
    @classmethod
    def _validate_db_url(cls, v: str) -> str:
        # Cheap sanity check without requiring pydantic's strict PostgresDsn parsing
        # (which rejects the +psycopg2 driver suffix by default).
        if not v.startswith(("postgresql://", "postgresql+psycopg2://")):
            raise ValueError("database_url must be a postgresql:// or postgresql+psycopg2:// URL")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
