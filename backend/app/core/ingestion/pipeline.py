"""Ingestion pipeline — state machine orchestrator.

Manages the full document processing lifecycle:
queued → parsing → chunking → persisting → embedding → ready | error

Runs as background tasks with semaphore-limited concurrency.
Implements two-branch retry logic based on stored chunk state.
"""

import asyncio
import logging
import uuid
import time
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Document
from app.core.ingestion.loader import load_document
from app.core.ingestion.chunker import chunk_document
from app.core.ingestion.chunk_store import (
    persist_chunks,
    get_unembedded_chunks,
    count_chunks,
    mark_chunks_embedded,
)
from app.core.ingestion.embedder import embed_texts_dense, embed_texts_sparse
from app.db.vector_store import vector_store

logger = logging.getLogger(__name__)

# Semaphore to limit concurrent ingestions
_ingestion_semaphore = asyncio.Semaphore(settings.max_concurrent_ingestions)
_thread_pool = ThreadPoolExecutor(max_workers=settings.max_concurrent_ingestions)


def _update_status(db: Session, doc: Document, status: str, error: str = None):
    """Update document status in SQLite."""
    doc.status = status
    if error:
        doc.error_message = error
    db.commit()


def _run_ingestion_sync(doc_id: str, db_factory):
    """Synchronous ingestion worker — runs in thread pool.

    This is the main processing function that handles the full pipeline.
    It runs synchronously in a thread to avoid blocking the event loop.
    """
    from app.db.database import SessionLocal

    db = db_factory()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            logger.error(f"Document {doc_id} not found")
            return

        kb = doc.knowledge_base
        collection_name = f"kb_{kb.id}"

        # ── Stage 1: Parsing ──
        _update_status(db, doc, "parsing")
        try:
            pages = load_document(doc.file_path, doc.file_type)
            if not pages:
                _update_status(db, doc, "error", "No content extracted from document")
                return
        except Exception as e:
            _update_status(db, doc, "error", f"Parsing failed: {str(e)}")
            logger.exception(f"Parsing failed for {doc_id}")
            return

        # ── Stage 2: Chunking ──
        _update_status(db, doc, "chunking")
        try:
            chunks = chunk_document(pages)
            if not chunks:
                _update_status(db, doc, "error", "No chunks created from document")
                return
            doc.chunk_count = len(chunks)
            db.commit()
        except Exception as e:
            _update_status(db, doc, "error", f"Chunking failed: {str(e)}")
            logger.exception(f"Chunking failed for {doc_id}")
            return

        # ── Stage 3: Persisting chunks to SQLite ──
        _update_status(db, doc, "persisting")
        try:
            persist_chunks(db, doc_id, chunks)
        except Exception as e:
            _update_status(db, doc, "error", f"Chunk persistence failed: {str(e)}")
            logger.exception(f"Chunk persistence failed for {doc_id}")
            return

        # ── Stage 4: Embedding + indexing to Qdrant ──
        # Ensure collection exists (in-memory Qdrant loses collections on restart)
        if not vector_store.collection_exists(collection_name):
            vector_store.create_collection(collection_name, kb.embedding_dimension)
        _embed_chunks(db, doc, collection_name)

    except Exception as e:
        logger.exception(f"Unexpected error in ingestion for {doc_id}: {e}")
        try:
            _update_status(db, doc, "error", f"Unexpected error: {str(e)}")
        except Exception:
            pass
    finally:
        db.close()


def _embed_chunks(db: Session, doc: Document, collection_name: str):
    """Embed and index chunks to Qdrant. Used for both initial ingestion and retry."""
    _update_status(db, doc, "embedding")

    chunks_to_embed = get_unembedded_chunks(db, doc.id, start_from=doc.last_successful_chunk)

    if not chunks_to_embed:
        _update_status(db, doc, "ready")
        return

    # Process in batches
    batch_size = 32
    for i in range(0, len(chunks_to_embed), batch_size):
        batch = chunks_to_embed[i:i + batch_size]
        texts = [c.content for c in batch]

        try:
            # Generate embeddings
            dense_vectors = embed_texts_dense(texts)
            sparse_vectors = embed_texts_sparse(texts)

            # Prepare payloads
            # Convert chunk IDs to UUIDs — Qdrant requires UUID point IDs
            point_ids = [str(uuid.uuid5(uuid.NAMESPACE_DNS, c.id)) for c in batch]
            payloads = [
                {
                    "content": c.content,
                    "document_id": doc.id,
                    "kb_id": doc.kb_id,
                    "source_filename": (c.metadata_ or {}).get("source_filename", doc.filename),
                    "page_number": (c.metadata_ or {}).get("page_number", 0),
                    "chunk_index": c.index,
                }
                for c in batch
            ]

            # Upsert to Qdrant
            vector_store.upsert_points(
                collection_name=collection_name,
                point_ids=point_ids,
                dense_vectors=dense_vectors,
                sparse_vectors=sparse_vectors,
                payloads=payloads,
            )

            # Mark as embedded using ORIGINAL chunk IDs (not UUID point IDs)
            original_chunk_ids = [c.id for c in batch]
            mark_chunks_embedded(db, original_chunk_ids)
            doc.last_successful_chunk = batch[-1].index
            db.commit()

        except Exception as e:
            _update_status(db, doc, "error", f"Embedding failed at chunk {batch[0].index}: {str(e)}")
            logger.exception(f"Embedding failed for {doc.id} at batch starting {batch[0].index}")
            return

    _update_status(db, doc, "ready")
    logger.info(f"Document {doc.id} ({doc.filename}) ingestion complete")


async def start_ingestion(doc_id: str, db_factory):
    """Start document ingestion as a background task with concurrency limiting."""
    async with _ingestion_semaphore:
        loop = asyncio.get_event_loop()
        try:
            await asyncio.wait_for(
                loop.run_in_executor(_thread_pool, _run_ingestion_sync, doc_id, db_factory),
                timeout=settings.ingestion_timeout_seconds,
            )
        except asyncio.TimeoutError:
            # Mark as error on timeout
            db = db_factory()
            try:
                doc = db.query(Document).filter(Document.id == doc_id).first()
                if doc:
                    _update_status(db, doc, "error", "Ingestion timed out")
            finally:
                db.close()


async def retry_document(doc_id: str, db_factory):
    """Retry a failed document — uses two-branch logic.

    If chunks exist in SQLite: skip parsing/chunking, resume embedding.
    If no chunks stored: restart full pipeline from parsing.
    """
    db = db_factory()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise ValueError(f"Document {doc_id} not found")
        if doc.status != "error":
            raise ValueError(f"Document {doc_id} is not in error state (status={doc.status})")

        stored_chunk_count = count_chunks(db, doc_id)

        if stored_chunk_count == 0:
            # No chunks stored — failure was before persistence
            # Restart from beginning
            doc.status = "queued"
            doc.error_message = None
            doc.last_successful_chunk = 0
            db.commit()
            logger.info(f"Retrying {doc_id} from parsing (no stored chunks)")
            asyncio.create_task(start_ingestion(doc_id, db_factory))
        else:
            # Chunks exist — failure was during embedding
            # Resume embedding from where we left off
            doc.error_message = None
            kb = doc.knowledge_base
            collection_name = f"kb_{kb.id}"
            db.commit()
            logger.info(f"Retrying {doc_id} from embedding (chunk {doc.last_successful_chunk + 1})")

            async def _retry_embed():
                async with _ingestion_semaphore:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        _thread_pool,
                        lambda: _retry_embed_sync(doc_id, collection_name, db_factory),
                    )

            asyncio.create_task(_retry_embed())
    finally:
        db.close()


def _retry_embed_sync(doc_id: str, collection_name: str, db_factory):
    """Synchronous retry embedding worker."""
    db = db_factory()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            _embed_chunks(db, doc, collection_name)
    finally:
        db.close()
