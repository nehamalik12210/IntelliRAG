"""IntelliRAG configuration management using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM Providers ──
    openrouter_api_key: str = ""
    gemini_api_key: str = ""
    google_api_key: str = ""
    groq_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    default_llm_provider: str = "groq"
    default_llm_model: str = "llama-3.1-8b-instant"

    # ── Embeddings ──
    embedding_provider: str = "local"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # ── Retrieval ──
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k_retrieval: int = 20
    top_k_rerank: int = 5
    reranker_enabled: bool = True
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker_cache_size: int = 1000

    hybrid_fusion_method: str = "rrf"
    hybrid_search_weight: float = 0.5
    sparse_model: str = "prithivida/Splade_PP_en_v1"

    # ── Storage ──
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    sqlite_db_path: str = "./data/intellirag.db"
    upload_dir: str = "./data/uploads"

    # ── Ingestion ──
    max_concurrent_ingestions: int = 3
    ingestion_timeout_seconds: int = 300
    max_file_size_mb: int = 50

    # ── Agent Mode ──
    enable_web_search: bool = False
    web_search_api_key: str = ""
    web_search_provider: str = "tavily"

    # ── Server ──
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_port: int = 3000
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def db_path(self) -> Path:
        path = Path(self.sqlite_db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


settings = Settings()
