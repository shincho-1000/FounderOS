"""
Pydantic schemas for the three-tier memory system (MongoDB):
short-term (exact recent turns), summary (compressed older history),
long-term (durable facts).
"""
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MemoryCategory(str, Enum):
    goal = "goal"
    constraint = "constraint"
    past_decision = "past_decision"
    preference = "preference"
    metric = "metric"


# ── Long-term ────────────────────────────────────────────────────────────────
class LongTermEntryCreate(BaseModel):
    category: MemoryCategory
    content: str = Field(..., min_length=3, max_length=1000)
    importance: int = Field(3, ge=1, le=5)

    @field_validator("content", mode="before")
    @classmethod
    def _strip_content(cls, v: Any) -> Any:
        return v.strip() if isinstance(v, str) else v


class LongTermEntryOut(BaseModel):
    id: str
    business_id: str
    category: MemoryCategory
    content: str
    importance: int
    created_at: datetime
    updated_at: datetime


# ── Short-term ───────────────────────────────────────────────────────────────
class ShortTermEntryOut(BaseModel):
    id: str
    question: str
    answer_summary: str
    # Decision ids are UUID strings in this project (see orm/decision.py).
    decision_id: Optional[str] = None
    created_at: datetime


# ── Summary ──────────────────────────────────────────────────────────────────
class MemorySummaryOut(BaseModel):
    summary: str = ""
    interactions_summarized: int = 0
    updated_at: Optional[datetime] = None


# ── Combined view (what the decision engine sees) ────────────────────────────
class MemoryContext(BaseModel):
    short_term: list[ShortTermEntryOut] = Field(default_factory=list)
    summary: str = ""
    long_term: list[LongTermEntryOut] = Field(default_factory=list)


# ── Backward-compatible names (re-exported by schemas/__init__.py) ───────────
LongTermMemoryCreate = LongTermEntryCreate
LongTermMemoryOut = LongTermEntryOut
ShortTermEntry = ShortTermEntryOut


class ShortTermMemoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    business_id: str
    entries: list[ShortTermEntryOut] = Field(default_factory=list)


# ── Mongo helper ─────────────────────────────────────────────────────────────
def serialize_doc(doc: dict) -> dict:
    """Return a copy of a Mongo document with `_id` (ObjectId) exposed as `id` (str).

    The single place where ObjectId is converted, so it never leaks into responses.
    """
    out = dict(doc)
    if "_id" in out:
        out["id"] = str(out.pop("_id"))
    return out
