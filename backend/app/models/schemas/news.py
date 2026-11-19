"""
Pydantic schemas for news articles.
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class NewsItem(BaseModel):
    title: str
    source: str
    url: str
    published_at: Optional[datetime] = None
    snippet: Optional[str] = None


class NewsResponse(BaseModel):
    query: str
    articles: list[NewsItem] = []
    cached: bool = False
