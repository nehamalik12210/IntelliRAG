"""Pydantic schemas for knowledge base API."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class KBCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field("", max_length=1000)


class KBResponse(BaseModel):
    id: str
    name: str
    description: str
    embedding_model: str
    embedding_dimension: int
    document_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class KBListResponse(BaseModel):
    knowledge_bases: list[KBResponse]
    total: int
