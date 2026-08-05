"""Embedding service — generates dense and sparse vectors.

Uses FastEmbed for local embeddings (integrates natively with Qdrant)
or OpenAI for cloud embeddings. Sparse vectors use SPLADE model.
"""

import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Module-level singletons (lazy-loaded)
_dense_model = None
_sparse_model = None


def _get_dense_model():
    """Lazy-load the dense embedding model."""
    global _dense_model
    if _dense_model is None:
        if settings.embedding_provider == "local":
            from fastembed import TextEmbedding
            _dense_model = TextEmbedding(model_name=settings.embedding_model)
            logger.info(f"Loaded dense model: {settings.embedding_model}")
        elif settings.embedding_provider == "openai":
            from langchain_openai import OpenAIEmbeddings
            _dense_model = OpenAIEmbeddings(
                model=settings.embedding_model,
                openai_api_key=settings.openai_api_key,
            )
            logger.info(f"Using OpenAI embeddings: {settings.embedding_model}")
        else:
            raise ValueError(f"Unknown embedding provider: {settings.embedding_provider}")
    return _dense_model


def _get_sparse_model():
    """Lazy-load the sparse (SPLADE) embedding model."""
    global _sparse_model
    if _sparse_model is None:
        from fastembed import SparseTextEmbedding
        _sparse_model = SparseTextEmbedding(model_name=settings.sparse_model)
        logger.info(f"Loaded sparse model: {settings.sparse_model}")
    return _sparse_model


def embed_texts_dense(texts: list[str]) -> list[list[float]]:
    """Generate dense embeddings for a list of texts.

    Returns a list of embedding vectors.
    """
    model = _get_dense_model()

    if settings.embedding_provider == "local":
        # FastEmbed returns a generator
        embeddings = list(model.embed(texts))
        return [emb.tolist() for emb in embeddings]
    elif settings.embedding_provider == "openai":
        # LangChain OpenAI embeddings
        return model.embed_documents(texts)
    else:
        raise ValueError(f"Unknown embedding provider: {settings.embedding_provider}")


def embed_query_dense(query: str) -> list[float]:
    """Generate a dense embedding for a single query."""
    model = _get_dense_model()

    if settings.embedding_provider == "local":
        embeddings = list(model.embed([query]))
        return embeddings[0].tolist()
    elif settings.embedding_provider == "openai":
        return model.embed_query(query)
    else:
        raise ValueError(f"Unknown embedding provider: {settings.embedding_provider}")


def embed_texts_sparse(texts: list[str]) -> list[dict]:
    """Generate sparse (SPLADE) embeddings for a list of texts.

    Returns list of dicts with 'indices' and 'values' for each text.
    Note: SPLADE produces learned sparse weights, NOT traditional BM25.
    """
    model = _get_sparse_model()
    embeddings = list(model.embed(texts))

    results = []
    for emb in embeddings:
        results.append({
            "indices": emb.indices.tolist(),
            "values": emb.values.tolist(),
        })
    return results


def embed_query_sparse(query: str) -> dict:
    """Generate a sparse embedding for a single query."""
    model = _get_sparse_model()
    embeddings = list(model.embed([query]))
    emb = embeddings[0]
    return {
        "indices": emb.indices.tolist(),
        "values": emb.values.tolist(),
    }


def validate_embedding_dimension(expected_dim: int) -> bool:
    """Validate that the current embedding model produces the expected dimension.

    Used to prevent dimension mismatches when adding documents to existing KBs.
    """
    test_embedding = embed_texts_dense(["dimension test"])
    actual_dim = len(test_embedding[0])
    if actual_dim != expected_dim:
        logger.error(
            f"Embedding dimension mismatch: expected {expected_dim}, "
            f"got {actual_dim} from model '{settings.embedding_model}'"
        )
        return False
    return True
