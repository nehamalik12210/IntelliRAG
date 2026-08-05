"""Retrieval settings API — configure search and reranking at runtime."""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional

from app.config import settings
from app.core.retrieval.reranker import cache_info as reranker_cache_info

router = APIRouter(prefix="/api/settings", tags=["settings"])


class RetrievalSettingsResponse(BaseModel):
    """Current retrieval configuration."""
    fusion_method: str
    hybrid_search_weight: float
    top_k_retrieval: int
    top_k_rerank: int
    reranker_enabled: bool
    reranker_model: str
    reranker_cache: Optional[dict] = None
    sparse_model: str
    chunk_size: int
    chunk_overlap: int


class RetrievalSettingsUpdate(BaseModel):
    """Updatable retrieval settings (runtime only, doesn't persist to .env)."""
    fusion_method: Optional[str] = Field(None, pattern="^(rrf|weighted_sum|dense_only)$")
    hybrid_search_weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    top_k_retrieval: Optional[int] = Field(None, ge=1, le=100)
    top_k_rerank: Optional[int] = Field(None, ge=1, le=50)
    reranker_enabled: Optional[bool] = None


@router.get("/retrieval", response_model=RetrievalSettingsResponse)
async def get_retrieval_settings():
    """Get current retrieval configuration and reranker cache stats."""
    cache = None
    try:
        cache = reranker_cache_info()
    except Exception:
        pass

    return RetrievalSettingsResponse(
        fusion_method=settings.hybrid_fusion_method,
        hybrid_search_weight=settings.hybrid_search_weight,
        top_k_retrieval=settings.top_k_retrieval,
        top_k_rerank=settings.top_k_rerank,
        reranker_enabled=settings.reranker_enabled,
        reranker_model=settings.reranker_model,
        reranker_cache=cache,
        sparse_model=settings.sparse_model,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )


@router.put("/retrieval", response_model=RetrievalSettingsResponse)
async def update_retrieval_settings(update: RetrievalSettingsUpdate):
    """Update retrieval settings at runtime.

    Changes are applied immediately but do NOT persist to .env.
    They will reset on server restart.
    """
    if update.fusion_method is not None:
        settings.hybrid_fusion_method = update.fusion_method
    if update.hybrid_search_weight is not None:
        settings.hybrid_search_weight = update.hybrid_search_weight
    if update.top_k_retrieval is not None:
        settings.top_k_retrieval = update.top_k_retrieval
    if update.top_k_rerank is not None:
        settings.top_k_rerank = update.top_k_rerank
    if update.reranker_enabled is not None:
        settings.reranker_enabled = update.reranker_enabled

    return await get_retrieval_settings()
