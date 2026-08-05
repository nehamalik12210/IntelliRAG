"""SQLAlchemy database models for IntelliRAG.

All models include `created_by` for future multi-tenancy support.
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship


def utcnow():
    return datetime.now(timezone.utc)


def new_id():
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class KnowledgeBase(Base):
    """A knowledge base is a named collection of documents with a fixed embedding model."""

    __tablename__ = "knowledge_bases"

    id = Column(String, primary_key=True, default=new_id)
    name = Column(String, nullable=False)
    description = Column(String, default="")
    created_by = Column(String, default="default", index=True)
    embedding_model = Column(String, nullable=False)
    embedding_dimension = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    documents = relationship("Document", back_populates="knowledge_base", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="knowledge_base")


class Document(Base):
    """A document uploaded to a knowledge base, tracked through the ingestion pipeline."""

    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=new_id)
    kb_id = Column(String, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(Integer, default=0)
    file_path = Column(String, nullable=True)

    # Ingestion state machine
    status = Column(String, default="queued")  # queued|parsing|chunking|persisting|embedding|ready|error
    error_message = Column(String, nullable=True)
    chunk_count = Column(Integer, default=0)
    last_successful_chunk = Column(Integer, default=0)

    created_by = Column(String, default="default", index=True)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_documents_kb_id", "kb_id"),
    )


class DocumentChunk(Base):
    """Persisted chunks — ensures retry re-embeds the SAME chunks (no re-chunking).

    Chunk IDs are deterministic: '{doc_id}_chunk_{index}' so they are stable
    across retry attempts. This is the critical invariant that makes resumable
    embedding work correctly.
    """

    __tablename__ = "document_chunks"

    id = Column(String, primary_key=True)  # Deterministic: "{doc_id}_chunk_{index}"
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True)  # {filename, page_number, section_title}
    is_embedded = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    document = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("ix_document_chunks_document_id", "document_id"),
    )


class Conversation(Base):
    """A chat conversation, optionally linked to a knowledge base."""

    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=new_id)
    kb_id = Column(String, ForeignKey("knowledge_bases.id", ondelete="SET NULL"), nullable=True)
    title = Column(String, default="New Chat")
    created_by = Column(String, default="default", index=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    knowledge_base = relationship("KnowledgeBase", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan",
                            order_by="Message.created_at")


class Message(Base):
    """A single message in a conversation.

    Supports multiple message types beyond simple user/assistant text:
    - text: Normal chat message
    - action_required: Agent fallback prompt with action buttons
    - tool_indicator: Shows which tool was used (e.g., "Searched KB")
    """

    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=new_id)
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)  # user | assistant | system | action_required
    content = Column(Text, nullable=False)
    message_type = Column(String, default="text")  # text | action_required | tool_indicator
    action_payload = Column(JSON, nullable=True)  # For action_required: {action_id, possible_actions, expires_at}
    sources = Column(JSON, nullable=True)  # [{filename, page, chunk_id, score}]
    feedback = Column(String, nullable=True)  # thumbs_up | thumbs_down | null
    feedback_comment = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        Index("ix_messages_conversation_id", "conversation_id"),
    )


class QueryLog(Base):
    """Stores full retrieval traces for evaluation and debugging."""

    __tablename__ = "query_logs"

    id = Column(String, primary_key=True, default=new_id)
    conversation_id = Column(String, nullable=True)
    message_id = Column(String, nullable=True)
    query = Column(Text, nullable=False)
    kb_id = Column(String, nullable=True)
    retrieved_chunks = Column(JSON, nullable=True)  # [{chunk_id, content, score, source}]
    retrieval_method = Column(String, nullable=True)  # dense | hybrid_rrf | hybrid_weighted
    retrieval_latency_ms = Column(Integer, nullable=True)
    response = Column(Text, nullable=True)
    model_used = Column(String, nullable=True)

    # RAGAS metrics (backfilled asynchronously)
    faithfulness_score = Column(String, nullable=True)
    answer_relevancy_score = Column(String, nullable=True)
    context_precision_score = Column(String, nullable=True)

    created_at = Column(DateTime, default=utcnow)
