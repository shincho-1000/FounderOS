"""
Pydantic schemas for document upload and RAG queries.
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class DocumentUploadResponse(BaseModel):
    id: str
    filename: str
    business_id: str
    chunk_count: int
    uploaded_at: datetime


class DocumentOut(BaseModel):
    id: str
    filename: str
    business_id: str
    uploaded_at: datetime


class DocumentQueryRequest(BaseModel):
    question: str
    top_k: int = 4


class DocumentChunk(BaseModel):
    text: str
    score: Optional[float] = None
    source_file: Optional[str] = None


class DocumentQueryResponse(BaseModel):
    question: str
    answer: str
    chunks: list[DocumentChunk] = []
