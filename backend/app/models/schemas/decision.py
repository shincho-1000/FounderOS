"""
Pydantic schemas for decisions — the core feature.
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class OptionAnalysis(BaseModel):
    option: str
    pros: list[str]
    cons: list[str]


class SourcesUsed(BaseModel):
    memory: bool = False
    news: list[str] = []
    docs: list[str] = []


class DecisionRequest(BaseModel):
    question: str
    options: Optional[list[str]] = None


class DecisionOutput(BaseModel):
    """Structured output schema sent to Gemini for JSON generation."""
    recommendation: str
    reasoning: str
    options_considered: list[OptionAnalysis] = []
    risks: list[str] = []
    next_steps: list[str] = []
    confidence: float  # 0-1
    sources_used: SourcesUsed = SourcesUsed()


class DecisionOut(BaseModel):
    id: str
    business_id: str
    question: str
    recommendation: Optional[str] = None
    reasoning: Optional[str] = None
    risks: Optional[list[str]] = None
    confidence: Optional[float] = None
    context_snapshot: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}
