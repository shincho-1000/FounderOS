"""
Pydantic schemas for business insight reports.
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class InsightReport(BaseModel):
    """Structured output schema sent to Gemini for insight generation."""
    summary: str
    opportunities: list[str] = []
    threats: list[str] = []
    market_trends: list[str] = []
    recommended_priorities: list[str] = []
    kpis_to_track: list[str] = []


class InsightOut(BaseModel):
    id: str
    business_id: str
    report: InsightReport
    created_at: datetime


class InsightLatest(BaseModel):
    report: Optional[InsightReport] = None
    generated_at: Optional[datetime] = None
    cached: bool = False
