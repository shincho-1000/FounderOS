"""
DuckDuckGo news adapter stub (Phase 5 stretch adapter).
"""
from app.news.base import NewsAdapter, NewsItem


class DuckDuckGoAdapter(NewsAdapter):
    provider_name: str = "duckduckgo"

    async def fetch(self, query: str, limit: int = 10) -> list[NewsItem]:
        raise NotImplementedError("DuckDuckGoAdapter is not implemented in Phase 5")
