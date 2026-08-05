"""Document API — upload, status, retry, and deletion."""

import asyncio
import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.db.database import get_db, SessionLocal
from app.db.models import KnowledgeBase, Document
from app.db.vector_store import vector_store
from app.core.ingestion.pipeline import start_ingestion, retry_document
from app.core.ingestion.chunk_store import delete_chunks, count_chunks
from app.schemas.documents import DocumentResponse, DocumentStatusResponse, DocumentListResponse
from app.config import settings

router = APIRouter(prefix="/api/documents", tags=["documents"])
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md", "csv", "pptx", "html", "htm"}


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    kb_id: str = Form(...),
    db: Session = Depends(get_db),
):
    """Upload a document to a knowledge base for async processing.

    The document enters the ingestion pipeline immediately:
    queued → parsing → chunking → persisting → embedding → ready
    """
    # Validate KB exists
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(404, "Knowledge base not found")

    # Validate embedding dimension matches
    if kb.embedding_model != settings.embedding_model:
        raise HTTPException(
            400,
            f"This KB uses '{kb.embedding_model}' ({kb.embedding_dimension} dims). "
            f"Your current config uses '{settings.embedding_model}' ({settings.embedding_dimension} dims). "
            f"Change your embedding model or create a new KB."
        )

    # Validate file type
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: .{ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    # Validate file size
    content = await file.read()
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(400, f"File too large. Maximum: {settings.max_file_size_mb}MB")

    # Save file to disk
    upload_dir = settings.upload_path / kb_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / file.filename
    # Handle duplicate filenames
    counter = 1
    while file_path.exists():
        stem = Path(file.filename).stem
        file_path = upload_dir / f"{stem}_{counter}.{ext}"
        counter += 1

    with open(file_path, "wb") as f:
        f.write(content)

    # Create document record
    doc = Document(
        kb_id=kb_id,
        filename=file.filename,
        file_type=ext,
        file_size=len(content),
        file_path=str(file_path),
        status="queued",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Start background ingestion
    asyncio.create_task(start_ingestion(doc.id, SessionLocal))

    logger.info(f"Uploaded '{file.filename}' to KB '{kb.name}' (doc_id={doc.id})")

    return DocumentResponse(
        id=doc.id,
        kb_id=doc.kb_id,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        status=doc.status,
        chunk_count=doc.chunk_count,
        created_at=doc.created_at.isoformat() if doc.created_at else None,
    )


@router.get("/{kb_id}", response_model=DocumentListResponse)
async def list_documents(kb_id: str, db: Session = Depends(get_db)):
    """List all documents in a knowledge base."""
    docs = db.query(Document).filter(
        Document.kb_id == kb_id
    ).order_by(Document.created_at.desc()).all()

    return DocumentListResponse(
        documents=[
            DocumentResponse(
                id=d.id,
                kb_id=d.kb_id,
                filename=d.filename,
                file_type=d.file_type,
                file_size=d.file_size,
                status=d.status,
                error_message=d.error_message,
                chunk_count=d.chunk_count,
                created_at=d.created_at.isoformat() if d.created_at else None,
            )
            for d in docs
        ],
        total=len(docs),
    )


@router.get("/{doc_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(doc_id: str, db: Session = Depends(get_db)):
    """Get document processing status and progress."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")

    return DocumentStatusResponse(
        id=doc.id,
        status=doc.status,
        progress=doc.last_successful_chunk,
        total=doc.chunk_count,
        error_message=doc.error_message,
    )


@router.post("/{doc_id}/retry")
async def retry_failed_document(doc_id: str, db: Session = Depends(get_db)):
    """Retry a failed document using two-branch logic.

    If chunks exist → skip to embedding.
    If no chunks → restart from parsing.
    """
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    if doc.status != "error":
        raise HTTPException(400, f"Document is not in error state (status={doc.status})")

    stored = count_chunks(db, doc_id)
    retry_from = "embedding" if stored > 0 else "parsing"

    await retry_document(doc_id, SessionLocal)

    return {"status": "retrying", "retry_from": retry_from, "stored_chunks": stored}


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, db: Session = Depends(get_db)):
    """Delete a document, its chunks from SQLite, and vectors from Qdrant."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")

    # Delete vectors from Qdrant
    collection_name = f"kb_{doc.kb_id}"
    try:
        vector_store.delete_by_document(collection_name, doc_id)
    except Exception as e:
        logger.warning(f"Failed to delete vectors for {doc_id}: {e}")

    # Delete file from disk
    if doc.file_path:
        try:
            Path(doc.file_path).unlink(missing_ok=True)
        except Exception:
            pass

    # SQLAlchemy cascade handles chunks
    db.delete(doc)
    db.commit()

    return {"status": "deleted", "id": doc_id}
