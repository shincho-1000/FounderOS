"""
Pydantic schemas for short-term and long-term memory (MongoDB).
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class LongTermMemoryCreate(BaseModel):
    category: str = Field(
        ...,
        description="One of: goal, constraint, past_decision, preference, metric"
    )
    content: str
    importance: int = Field(default=3, ge=1, le=5)


class LongTermMemoryOut(BaseModel):
    id: str = Field(alias="_id", default=None)
    business_id: str
    category: str
    content: str
    importance: int
    created_at: datetime

    model_config = {"populate_by_name": True}


class ShortTermEntry(BaseModel):
    question: str
    answer_summary: str
    timestamp: datetime


class ShortTermMemoryOut(BaseModel):
    business_id: str
    entries: list[ShortTermEntry] = []


class MemoryContext(BaseModel):
    """Combined memory context used by the decision engine."""
    short_term: list[ShortTermEntry] = []
    long_term: list[LongTermMemoryOut] = []
