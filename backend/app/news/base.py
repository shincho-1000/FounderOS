"""
Base adapter interface and normalized NewsItem model for the News Engine.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RateLimitError(Exception):
    """Raised when an upstream news provider signals rate limiting (e.g. HTTP 429)."""


class NewsItem(BaseModel):
    title: str
    source: str
    url: str
    published_at: Optional[datetime] = None
    snippet: str = ""
    country: Optional[str] = None


class NewsAdapter(ABC):
    """Abstract base class for all news provider adapters."""

    provider_name: str = "base"

    @abstractmethod
    async def fetch(self, query: str, limit: int = 10) -> list[NewsItem]:
        """Fetch up to `limit` news items matching `query`."""
        raise NotImplementedError
