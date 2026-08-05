"""Hybrid search module — RRF and weighted-sum fusion.

Implements two fusion strategies:
1. RRF (default): Uses Qdrant's native FusionQuery — single API call, no tuning needed.
2. Weighted Sum: Manual separate queries + score normalization + linear combination.
   Requires HYBRID_SEARCH_WEIGHT config. More control but more complex.

Usage:
    from app.core.retrieval.hybrid_search import retrieve
    results = retrieve(collection, query_text, method="rrf", limit=20)
"""

import logging
from enum import Enum
from typing import Optional

from qdrant_client import models

from app.config import settings
from app.db.vector_store import vector_store
from app.core.ingestion.embedder import (
    embed_query_dense,
    embed_query_sparse,
)

logger = logging.getLogger(__name__)


class FusionMethod(str, Enum):
    RRF = "rrf"
    WEIGHTED_SUM = "weighted_sum"
    DENSE_ONLY = "dense_only"


def retrieve(
    collection_name: str,
    query: str,
    method: Optional[str] = None,
    limit: Optional[int] = None,
    dense_weight: Optional[float] = None,
    document_ids: Optional[list[str]] = None,
) -> list[dict]:
    """Main retrieval entry point — routes to the correct fusion strategy.

    Args:
        collection_name: Qdrant collection to search
        query: User's query text
        method: Fusion method (rrf | weighted_sum | dense_only). Default from config.
        limit: Max results. Default from config.
        dense_weight: Weight for dense in weighted_sum (0.0=pure sparse, 1.0=pure dense).
        document_ids: Optional list of document IDs to restrict search to specific documents.

    Returns:
        List of result dicts with 'id', 'score', 'payload'.
    """
    method = method or settings.hybrid_fusion_method
    limit = limit or settings.top_k_retrieval
    dense_weight = dense_weight if dense_weight is not None else settings.hybrid_search_weight

    logger.info(f"Retrieving from '{collection_name}' | method={method} | limit={limit} | doc_ids={document_ids}")

    query_filter = None
    if document_ids and len(document_ids) > 0:
        if len(document_ids) == 1:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=document_ids[0])
                    )
                ]
            )
        else:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchAny(any=document_ids)
                    )
                ]
            )

    if method == FusionMethod.DENSE_ONLY:
        return _search_dense_only(collection_name, query, limit, query_filter)
    elif method == FusionMethod.RRF:
        return _search_hybrid_rrf(collection_name, query, limit, query_filter)
    elif method == FusionMethod.WEIGHTED_SUM:
        return _search_hybrid_weighted(collection_name, query, limit, dense_weight, query_filter)
    else:
        logger.warning(f"Unknown fusion method '{method}', falling back to dense_only")
        return _search_dense_only(collection_name, query, limit, query_filter)


def _search_dense_only(
    collection_name: str,
    query: str,
    limit: int,
    query_filter: Optional[models.Filter] = None,
) -> list[dict]:
    """Dense-only semantic search — Phase 1 baseline."""
    query_vector = embed_query_dense(query)
    results = vector_store.search_dense(
        collection_name=collection_name,
        query_vector=query_vector,
        limit=limit,
        query_filter=query_filter,
    )
    for r in results:
        r["retrieval_method"] = "dense_only"
    return results


def _search_hybrid_rrf(
    collection_name: str,
    query: str,
    limit: int,
    query_filter: Optional[models.Filter] = None,
) -> list[dict]:
    """Hybrid search using Qdrant's native RRF fusion.

    Single API call — Qdrant handles the prefetch (dense + sparse)
    and fuses results using Reciprocal Rank Fusion (1/(rank + k)).
    No weight parameter needed. Works well out of the box.
    """
    dense_vector = embed_query_dense(query)
    sparse_vector = embed_query_sparse(query)

    results = vector_store.search_hybrid(
        collection_name=collection_name,
        dense_vector=dense_vector,
        sparse_vector=sparse_vector,
        limit=limit,
        query_filter=query_filter,
    )
    for r in results:
        r["retrieval_method"] = "hybrid_rrf"
    return results


def _search_hybrid_weighted(
    collection_name: str,
    query: str,
    limit: int,
    dense_weight: float,
    query_filter: Optional[models.Filter] = None,
) -> list[dict]:
    """Hybrid search using manual weighted sum of normalized scores.

    Cannot use Qdrant's FusionQuery here — it only supports RRF.
    Instead we:
    1. Query dense and sparse vectors separately
    2. Normalize scores (min-max per result set)
    3. Combine: final_score = dense_weight * dense_norm + (1 - dense_weight) * sparse_norm
    4. Re-sort and return top-k

    This gives explicit control over the dense/sparse balance but requires
    careful score normalization since dense (cosine similarity) and sparse
    (dot product) scores are on different scales.
    """
    dense_vector = embed_query_dense(query)
    sparse_vector = embed_query_sparse(query)

    # Fetch candidates separately — more than limit to get good coverage
    fetch_limit = limit * 3

    dense_results = vector_store.search_dense(
        collection_name=collection_name,
        query_vector=dense_vector,
        limit=fetch_limit,
        query_filter=query_filter,
    )

    sparse_results = vector_store.search_sparse(
        collection_name=collection_name,
        sparse_vector=sparse_vector,
        limit=fetch_limit,
        query_filter=query_filter,
    )

    # Normalize scores (min-max) for each result set
    dense_scores = _normalize_scores(dense_results)
    sparse_scores = _normalize_scores(sparse_results)

    # Merge into a single dict keyed by point ID
    combined = {}
    for r in dense_results:
        pid = r["id"]
        combined[pid] = {
            "id": pid,
            "payload": r["payload"],
            "dense_score": dense_scores.get(pid, 0.0),
            "sparse_score": 0.0,
        }

    for r in sparse_results:
        pid = r["id"]
        if pid in combined:
            combined[pid]["sparse_score"] = sparse_scores.get(pid, 0.0)
        else:
            combined[pid] = {
                "id": pid,
                "payload": r["payload"],
                "dense_score": 0.0,
                "sparse_score": sparse_scores.get(pid, 0.0),
            }

    # Compute weighted sum
    for pid, entry in combined.items():
        entry["score"] = (
            dense_weight * entry["dense_score"]
            + (1.0 - dense_weight) * entry["sparse_score"]
        )
        entry["retrieval_method"] = "hybrid_weighted"

    # Sort by combined score, take top-k
    ranked = sorted(combined.values(), key=lambda x: x["score"], reverse=True)[:limit]

    # Clean up internal fields
    results = []
    for r in ranked:
        results.append({
            "id": r["id"],
            "score": round(r["score"], 6),
            "payload": r["payload"],
            "retrieval_method": r["retrieval_method"],
            "dense_score": round(r["dense_score"], 6),
            "sparse_score": round(r["sparse_score"], 6),
        })

    logger.info(
        f"Weighted sum fusion: dense_weight={dense_weight}, "
        f"dense_candidates={len(dense_results)}, sparse_candidates={len(sparse_results)}, "
        f"merged={len(combined)}, returned={len(results)}"
    )
    return results


def _normalize_scores(results: list[dict]) -> dict[str, float]:
    """Min-max normalize scores to [0, 1] range.

    Returns a dict mapping point_id to normalized score.
    If all scores are equal, returns 0.5 for all (avoids division by zero).
    """
    if not results:
        return {}

    scores = [r["score"] for r in results]
    min_s = min(scores)
    max_s = max(scores)
    range_s = max_s - min_s

    if range_s == 0:
        return {r["id"]: 0.5 for r in results}

    return {
        r["id"]: (r["score"] - min_s) / range_s
        for r in results
    }
