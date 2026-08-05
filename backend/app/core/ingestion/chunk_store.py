"""Chunk persistence layer — stores chunks in SQLite for reliable retry.

After chunking, all chunk texts + metadata are written here with deterministic
IDs. On retry, the pipeline reads chunks from this store instead of re-chunking,
guaranteeing stable chunk IDs across attempts.
"""

import logging
from sqlalchemy.orm import Session

from app.db.models import DocumentChunk

logger = logging.getLogger(__name__)


def persist_chunks(
    db: Session,
    document_id: str,
    chunks: list[dict],
) -> list[DocumentChunk]:
    """Write chunk texts and metadata to SQLite with deterministic IDs.

    Args:
        db: SQLAlchemy session
        document_id: Parent document ID
        chunks: List of chunk dicts with 'content' and 'metadata'

    Returns:
        List of created DocumentChunk ORM objects
    """
    db_chunks = []
    for i, chunk in enumerate(chunks):
        chunk_id = f"{document_id}_chunk_{i}"
        db_chunk = DocumentChunk(
            id=chunk_id,
            document_id=document_id,
            index=i,
            content=chunk["content"],
            metadata_=chunk.get("metadata", {}),
            is_embedded=False,
        )
        db_chunks.append(db_chunk)

    db.bulk_save_objects(db_chunks)
    db.commit()

    logger.info(f"Persisted {len(db_chunks)} chunks for document '{document_id}'")
    return db_chunks


def get_unembedded_chunks(
    db: Session,
    document_id: str,
    start_from: int = 0,
) -> list[DocumentChunk]:
    """Retrieve chunks that haven't been embedded yet, starting from an index.

    Used during retry to skip already-embedded chunks.

    Args:
        db: SQLAlchemy session
        document_id: Parent document ID
        start_from: Start from this chunk index (inclusive)

    Returns:
        List of DocumentChunk objects to embed
    """
    return (
        db.query(DocumentChunk)
        .filter(
            DocumentChunk.document_id == document_id,
            DocumentChunk.index >= start_from,
            DocumentChunk.is_embedded == False,
        )
        .order_by(DocumentChunk.index)
        .all()
    )


def get_all_chunks(db: Session, document_id: str) -> list[DocumentChunk]:
    """Retrieve all persisted chunks for a document."""
    return (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.index)
        .all()
    )


def count_chunks(db: Session, document_id: str) -> int:
    """Count stored chunks for a document (used for retry branch decision)."""
    return (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
        .count()
    )


def mark_chunks_embedded(db: Session, chunk_ids: list[str]):
    """Mark chunks as successfully embedded."""
    db.query(DocumentChunk).filter(
        DocumentChunk.id.in_(chunk_ids)
    ).update({"is_embedded": True}, synchronize_session=False)
    db.commit()


def delete_chunks(db: Session, document_id: str):
    """Delete all chunks for a document (used during document deletion)."""
    db.query(DocumentChunk).filter(
        DocumentChunk.document_id == document_id
    ).delete(synchronize_session=False)
    db.commit()
    logger.info(f"Deleted chunks for document '{document_id}'")
