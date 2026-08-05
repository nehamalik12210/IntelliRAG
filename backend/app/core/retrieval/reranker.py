"""Cross-encoder reranker — runs in ThreadPoolExecutor to avoid blocking the event loop.

The cross-encoder model scores (query, passage) pairs with much higher precision
than bi-encoder similarity. However, it's CPU-intensive and must run off the
async event loop.

Features:
- ThreadPoolExecutor for async compatibility
- LRU cache on (query, chunk_content) pairs to avoid re-scoring
- Configurable top-k after reranking
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Module-level singletons
_reranker_model = None
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="reranker")


def _get_model():
    """Lazy-load the cross-encoder model."""
    global _reranker_model
    if _reranker_model is None:
        from sentence_transformers import CrossEncoder
        _reranker_model = CrossEncoder(settings.reranker_model)
        logger.info(f"Loaded reranker model: {settings.reranker_model}")
    return _reranker_model


@lru_cache(maxsize=settings.reranker_cache_size)
def _score_pair(query: str, passage: str) -> float:
    """Score a single (query, passage) pair. Cached by LRU.

    Cache size is controlled by RERANKER_CACHE_SIZE in config.
    """
    model = _get_model()
    score = model.predict([(query, passage)])[0]
    return float(score)


def _rerank_sync(
    query: str,
    results: list[dict],
    top_k: int,
) -> list[dict]:
    """Synchronous reranking — runs in a thread.

    Scores each result's content against the query using the cross-encoder,
    sorts by reranker score, and returns the top-k.
    """
    if not results:
        return results

    scored = []
    for r in results:
        content = r.get("payload", {}).get("content", "")
        if not content:
            # Skip chunks with no content
            continue

        rerank_score = _score_pair(query, content)
        scored.append({
            **r,
            "rerank_score": round(rerank_score, 6),
            "original_score": r.get("score", 0.0),
        })

    # Sort by reranker score (higher is better for cross-encoders)
    scored.sort(key=lambda x: x["rerank_score"], reverse=True)

    top_results = scored[:top_k]

    logger.info(
        f"Reranked {len(results)} → {len(top_results)} results "
        f"(top rerank_score={top_results[0]['rerank_score'] if top_results else 'N/A'})"
    )
    return top_results


async def rerank(
    query: str,
    results: list[dict],
    top_k: Optional[int] = None,
) -> list[dict]:
    """Async reranker — offloads cross-encoder scoring to ThreadPoolExecutor.

    This is the main entry point. It runs the CPU-intensive cross-encoder
    in a separate thread so it doesn't block the FastAPI event loop.

    Args:
        query: The user's query
        results: Retrieved results from hybrid search (list of dicts with 'payload.content')
        top_k: Number of results to return after reranking. Default from config.

    Returns:
        Reranked results with 'rerank_score' and 'original_score' fields added.
    """
    import asyncio

    if not settings.reranker_enabled:
        logger.debug("Reranker disabled, returning original results")
        return results[:top_k or settings.top_k_rerank]

    top_k = top_k or settings.top_k_rerank

    loop = asyncio.get_event_loop()
    reranked = await loop.run_in_executor(
        _executor,
        _rerank_sync,
        query,
        results,
        top_k,
    )
    return reranked


def clear_cache():
    """Clear the LRU cache (useful for testing or model changes)."""
    _score_pair.cache_clear()
    logger.info("Reranker cache cleared")


def cache_info():
    """Get cache statistics."""
    info = _score_pair.cache_info()
    return {
        "hits": info.hits,
        "misses": info.misses,
        "maxsize": info.maxsize,
        "currsize": info.currsize,
    }
