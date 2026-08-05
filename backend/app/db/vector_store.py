"""Qdrant vector store client wrapper.

Handles collection creation with dense + sparse vector params,
document indexing, hybrid search, and cleanup operations.
"""

import logging
from typing import Optional

from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse

from app.config import settings

logger = logging.getLogger(__name__)


class VectorStore:
    """Wrapper around Qdrant client for IntelliRAG vector operations."""

    def __init__(self):
        self.client: Optional[QdrantClient] = None

    def connect(self):
        """Initialize Qdrant client connection.

        Tries to connect to the configured Qdrant server first.
        Falls back to in-memory mode if the server is unavailable
        (no Docker needed for development).
        """
        try:
            kwargs = {"url": settings.qdrant_url, "timeout": 5}
            if settings.qdrant_api_key:
                kwargs["api_key"] = settings.qdrant_api_key
            client = QdrantClient(**kwargs)
            # Test connection
            client.get_collections()
            self.client = client
            logger.info(f"Connected to Qdrant at {settings.qdrant_url}")
        except Exception as e:
            logger.warning(f"Cannot reach Qdrant at {settings.qdrant_url}: {e}")
            logger.info("Falling back to persistent local Qdrant in data/qdrant_db")
            import os
            os.makedirs("data/qdrant_db", exist_ok=True)
            self.client = QdrantClient(path="data/qdrant_db")
            logger.info("Connected to local persistent Qdrant")

    def create_collection(self, collection_name: str, embedding_dim: int):
        """Create a Qdrant collection with dense + sparse vector support.

        Dense vectors are used for semantic search, sparse vectors (SPLADE)
        for keyword-style matching. Both are queried together via RRF fusion.
        """
        try:
            self.client.get_collection(collection_name)
            logger.info(f"Collection '{collection_name}' already exists")
            return
        except (UnexpectedResponse, Exception):
            pass

        self.client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "dense": models.VectorParams(
                    size=embedding_dim,
                    distance=models.Distance.COSINE,
                ),
            },
            sparse_vectors_config={
                "sparse": models.SparseVectorParams(
                    modifier=models.Modifier.IDF,  # Enable IDF for better BM25-like scoring
                ),
            },
        )
        logger.info(f"Created collection '{collection_name}' (dim={embedding_dim})")

    def delete_collection(self, collection_name: str):
        """Delete a collection and all its vectors."""
        try:
            self.client.delete_collection(collection_name)
            logger.info(f"Deleted collection '{collection_name}'")
        except Exception as e:
            logger.warning(f"Failed to delete collection '{collection_name}': {e}")

    def upsert_points(
        self,
        collection_name: str,
        point_ids: list[str],
        dense_vectors: list[list[float]],
        sparse_vectors: list[dict],
        payloads: list[dict],
    ):
        """Insert or update points with both dense and sparse vectors.

        Args:
            collection_name: Target Qdrant collection
            point_ids: Deterministic chunk IDs (e.g., "{doc_id}_chunk_{index}")
            dense_vectors: List of dense embedding vectors
            sparse_vectors: List of sparse vector dicts with 'indices' and 'values'
            payloads: List of metadata dicts for each point
        """
        points = []
        for pid, dense, sparse, payload in zip(point_ids, dense_vectors, sparse_vectors, payloads):
            vectors = {"dense": dense}
            if sparse and sparse.get("indices"):
                vectors["sparse"] = models.SparseVector(
                    indices=sparse["indices"],
                    values=sparse["values"],
                )
            points.append(models.PointStruct(
                id=pid,
                vector=vectors,
                payload=payload,
            ))

        # Batch upsert in groups of 100
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            self.client.upsert(
                collection_name=collection_name,
                points=batch,
            )
        logger.info(f"Upserted {len(points)} points to '{collection_name}'")

    def search_dense(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        query_filter: Optional[models.Filter] = None,
    ) -> list[dict]:
        """Dense-only vector search (Phase 1 default).

        Returns list of dicts with 'id', 'score', and 'payload'.
        """
        results = self.client.query_points(
            collection_name=collection_name,
            query=query_vector,
            using="dense",
            limit=limit,
            score_threshold=score_threshold,
            query_filter=query_filter,
        )

        return [
            {
                "id": str(point.id),
                "score": point.score,
                "payload": point.payload,
            }
            for point in results.points
        ]

    def search_hybrid(
        self,
        collection_name: str,
        dense_vector: list[float],
        sparse_vector: dict,
        limit: int = 10,
        query_filter: Optional[models.Filter] = None,
    ) -> list[dict]:
        """Hybrid search using Qdrant's native prefetch + RRF fusion (Phase 2).

        Combines dense semantic search with sparse keyword search using
        Reciprocal Rank Fusion. This is a single API call — no manual
        sync or score normalization needed.
        """
        sparse_qvec = models.SparseVector(
            indices=sparse_vector["indices"],
            values=sparse_vector["values"],
        )

        results = self.client.query_points(
            collection_name=collection_name,
            prefetch=[
                models.Prefetch(query=dense_vector, using="dense", limit=limit * 2, filter=query_filter),
                models.Prefetch(query=sparse_qvec, using="sparse", limit=limit * 2, filter=query_filter),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=limit,
        )

        return [
            {
                "id": str(point.id),
                "score": point.score,
                "payload": point.payload,
            }
            for point in results.points
        ]

    def search_sparse(
        self,
        collection_name: str,
        sparse_vector: dict,
        limit: int = 10,
        query_filter: Optional[models.Filter] = None,
    ) -> list[dict]:
        """Sparse-only search (Phase 2 fallback for weighted sum)."""
        sparse_qvec = models.SparseVector(
            indices=sparse_vector["indices"],
            values=sparse_vector["values"],
        )

        results = self.client.query_points(
            collection_name=collection_name,
            query=sparse_qvec,
            using="sparse",
            limit=limit,
            query_filter=query_filter,
        )

        return [
            {
                "id": str(point.id),
                "score": point.score,
                "payload": point.payload,
            }
            for point in results.points
        ]

    def delete_by_document(self, collection_name: str, document_id: str):
        """Delete all points belonging to a specific document."""
        self.client.delete(
            collection_name=collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        ),
                    ],
                ),
            ),
        )
        logger.info(f"Deleted points for document '{document_id}' from '{collection_name}'")

    def collection_exists(self, collection_name: str) -> bool:
        """Check if a collection exists."""
        try:
            self.client.get_collection(collection_name)
            return True
        except Exception:
            return False


# Singleton instance
vector_store = VectorStore()
