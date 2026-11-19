"""
Pydantic schemas for news articles and news API responses (Phase 5).
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NewsItemOut(BaseModel):
    title: str
    source: str
    url: str
    published_at: Optional[datetime] = None
    snippet: str = ""
    country: Optional[str] = None


# Backward-compatible alias for app.models.schemas.__init__
NewsItem = NewsItemOut


class NewsResponse(BaseModel):
    query: str
    provider: str
    cached: bool
    count: int
    items: list[NewsItemOut] = Field(default_factory=list)
