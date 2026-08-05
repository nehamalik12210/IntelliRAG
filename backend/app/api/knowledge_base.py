"""Knowledge Base API — CRUD operations for knowledge bases."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.db.models import KnowledgeBase, Document
from app.db.vector_store import vector_store
from app.schemas.knowledge_base import KBCreateRequest, KBResponse, KBListResponse
from app.core.ingestion.chunk_store import delete_chunks
from app.config import settings

router = APIRouter(prefix="/api/knowledge-bases", tags=["knowledge-bases"])
logger = logging.getLogger(__name__)


@router.post("", response_model=KBResponse)
async def create_knowledge_base(request: KBCreateRequest, db: Session = Depends(get_db)):
    """Create a new knowledge base.

    Records the current embedding model and dimension at creation time.
    These are locked — you cannot mix embedding models within a KB.
    """
    kb = KnowledgeBase(
        name=request.name,
        description=request.description,
        embedding_model=settings.embedding_model,
        embedding_dimension=settings.embedding_dimension,
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)

    # Create Qdrant collection
    collection_name = f"kb_{kb.id}"
    vector_store.create_collection(collection_name, kb.embedding_dimension)

    logger.info(f"Created KB '{kb.name}' (id={kb.id}, model={kb.embedding_model}, dim={kb.embedding_dimension})")

    return KBResponse(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        embedding_model=kb.embedding_model,
        embedding_dimension=kb.embedding_dimension,
        document_count=0,
        created_at=kb.created_at.isoformat() if kb.created_at else None,
        updated_at=kb.updated_at.isoformat() if kb.updated_at else None,
    )


@router.get("", response_model=KBListResponse)
async def list_knowledge_bases(db: Session = Depends(get_db)):
    """List all knowledge bases with document counts (single optimized query)."""
    doc_counts = (
        db.query(Document.kb_id, func.count(Document.id).label("cnt"))
        .group_by(Document.kb_id)
        .subquery()
    )

    rows = (
        db.query(KnowledgeBase, doc_counts.c.cnt)
        .outerjoin(doc_counts, KnowledgeBase.id == doc_counts.c.kb_id)
        .order_by(KnowledgeBase.created_at.desc())
        .all()
    )

    results = [
        KBResponse(
            id=kb.id,
            name=kb.name,
            description=kb.description,
            embedding_model=kb.embedding_model,
            embedding_dimension=kb.embedding_dimension,
            document_count=cnt or 0,
            created_at=kb.created_at.isoformat() if kb.created_at else None,
            updated_at=kb.updated_at.isoformat() if kb.updated_at else None,
        )
        for kb, cnt in rows
    ]

    return KBListResponse(knowledge_bases=results, total=len(results))


@router.get("/{kb_id}", response_model=KBResponse)
async def get_knowledge_base(kb_id: str, db: Session = Depends(get_db)):
    """Get a knowledge base by ID."""
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(404, "Knowledge base not found")

    doc_count = db.query(Document).filter(Document.kb_id == kb.id).count()

    return KBResponse(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        embedding_model=kb.embedding_model,
        embedding_dimension=kb.embedding_dimension,
        document_count=doc_count,
        created_at=kb.created_at.isoformat() if kb.created_at else None,
        updated_at=kb.updated_at.isoformat() if kb.updated_at else None,
    )


@router.delete("/{kb_id}")
async def delete_knowledge_base(kb_id: str, db: Session = Depends(get_db)):
    """Delete a knowledge base, all its documents, chunks, and vectors."""
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(404, "Knowledge base not found")

    # Delete Qdrant collection
    collection_name = f"kb_{kb.id}"
    vector_store.delete_collection(collection_name)

    # SQLAlchemy cascade handles documents and chunks
    db.delete(kb)
    db.commit()

    logger.info(f"Deleted KB '{kb.name}' (id={kb_id})")
    return {"status": "deleted", "id": kb_id}
