"""Pydantic schemas for chat API."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User's message")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID")
    kb_id: Optional[str] = Field(None, description="Knowledge base to search")
    document_ids: Optional[list[str]] = Field(None, description="Specific document IDs to filter by (multi-select)")
    provider: Optional[str] = Field(None, description="LLM provider override")
    model: Optional[str] = Field(None, description="Model name override")
    temperature: float = Field(0.7, ge=0, le=2)
    agent_mode: bool = Field(False, description="Enable agent/web search fallback")


class ChatSource(BaseModel):
    filename: str
    page_number: int
    chunk_id: str
    relevance_score: float
    content_preview: str


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    content: str
    sources: list[ChatSource] = []
    model_used: str = ""


class FeedbackRequest(BaseModel):
    message_id: str
    feedback: Optional[str] = Field(None, pattern="^(thumbs_up|thumbs_down)$")
    comment: Optional[str] = None


class ActionRequest(BaseModel):
    action_id: str
    chosen_action: str
    conversation_id: str
