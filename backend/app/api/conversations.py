"""Conversation API — CRUD for chat conversations."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from typing import Optional

from app.db.database import get_db
from app.db.models import Conversation, Message

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


class ConversationResponse(BaseModel):
    id: str
    kb_id: Optional[str] = None
    title: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    message_count: int = 0

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    message_type: str = "text"
    sources: Optional[list] = None
    feedback: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class ConversationCreateRequest(BaseModel):
    kb_id: Optional[str] = None
    title: str = Field("New Chat", max_length=200)


@router.get("")
async def list_conversations(db: Session = Depends(get_db)):
    """List all conversations, newest first. Uses a single optimized query."""
    # Single query with subquery join for message counts (avoids N+1)
    msg_counts = (
        db.query(Message.conversation_id, func.count(Message.id).label("cnt"))
        .group_by(Message.conversation_id)
        .subquery()
    )

    rows = (
        db.query(Conversation, msg_counts.c.cnt)
        .outerjoin(msg_counts, Conversation.id == msg_counts.c.conversation_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )

    results = [
        ConversationResponse(
            id=c.id,
            kb_id=c.kb_id,
            title=c.title,
            created_at=c.created_at.isoformat() if c.created_at else None,
            updated_at=c.updated_at.isoformat() if c.updated_at else None,
            message_count=cnt or 0,
        )
        for c, cnt in rows
    ]

    return {"conversations": results, "total": len(results)}


@router.post("", response_model=ConversationResponse)
async def create_conversation(request: ConversationCreateRequest, db: Session = Depends(get_db)):
    """Create a new conversation."""
    convo = Conversation(
        kb_id=request.kb_id,
        title=request.title,
    )
    db.add(convo)
    db.commit()
    db.refresh(convo)

    return ConversationResponse(
        id=convo.id,
        kb_id=convo.kb_id,
        title=convo.title,
        created_at=convo.created_at.isoformat() if convo.created_at else None,
        message_count=0,
    )


@router.get("/{conversation_id}/messages")
async def get_messages(conversation_id: str, db: Session = Depends(get_db)):
    """Get all messages for a conversation."""
    convo = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not convo:
        raise HTTPException(404, "Conversation not found")

    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).all()

    return {
        "conversation_id": conversation_id,
        "messages": [
            MessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                message_type=m.message_type or "text",
                sources=m.sources,
                feedback=m.feedback,
                created_at=m.created_at.isoformat() if m.created_at else None,
            )
            for m in messages
        ],
    }


class ConversationRenameRequest(BaseModel):
    title: str = Field(..., max_length=200)

@router.put("/{conversation_id}", response_model=ConversationResponse)
async def rename_conversation(conversation_id: str, request: ConversationRenameRequest, db: Session = Depends(get_db)):
    """Rename a conversation."""
    convo = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not convo:
        raise HTTPException(404, "Conversation not found")
        
    convo.title = request.title
    db.commit()
    db.refresh(convo)
    
    msg_count = db.query(Message).filter(Message.conversation_id == convo.id).count()
    return ConversationResponse(
        id=convo.id,
        kb_id=convo.kb_id,
        title=convo.title,
        created_at=convo.created_at.isoformat() if convo.created_at else None,
        updated_at=convo.updated_at.isoformat() if convo.updated_at else None,
        message_count=msg_count,
    )

@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Delete a conversation and all its messages."""
    convo = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not convo:
        raise HTTPException(404, "Conversation not found")

    db.delete(convo)
    db.commit()

    return {"status": "deleted", "id": conversation_id}
