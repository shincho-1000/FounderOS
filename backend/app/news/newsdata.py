"""
newsdata.io news adapter stub (Phase 5 stretch adapter).
"""
from app.news.base import NewsAdapter, NewsItem


class NewsDataAdapter(NewsAdapter):
    provider_name: str = "newsdata"

    async def fetch(self, query: str, limit: int = 10) -> list[NewsItem]:
        raise NotImplementedError("NewsDataAdapter is not implemented in Phase 5")
