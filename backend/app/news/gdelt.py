"""
GDELT DOC 2.0 API adapter (free, public, no API key required).
"""
import logging
import re
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.core.config import settings
from app.news.base import NewsAdapter, NewsItem, RateLimitError

logger = logging.getLogger(__name__)

USER_AGENT = "FounderOS-Hackathon/1.0"
_WHITESPACE_RE = re.compile(r"\s+")
_RATE_LIMIT_HINTS = ("rate limit", "too many requests", "please limit", "limit requests")


def _parse_seendate(raw: Optional[str]) -> Optional[datetime]:
    """Parse GDELT seendate 'YYYYMMDDTHHMMSSZ' to a timezone-aware UTC datetime."""
    if not raw or not isinstance(raw, str):
        return None
    try:
        return datetime.strptime(raw.strip(), "%Y%m%dT%H%M%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        logger.debug("Unparseable GDELT seendate: %r", raw)
        return None


def _normalize_title(title: str) -> str:
    return _WHITESPACE_RE.sub(" ", title.strip().lower())


class GdeltAdapter(NewsAdapter):
    """Adapter for GDELT DOC 2.0 article list endpoint."""

    provider_name: str = "gdelt"

    async def fetch(self, query: str, limit: int = 10) -> list[NewsItem]:
        max_records = min(250, max(limit, settings.NEWS_MAX_RECORDS))
        params = {
            "query": query,
            "mode": "artlist",
            "format": "json",
            "maxrecords": max_records,
            "timespan": settings.NEWS_TIMESPAN,
            "sort": "datedesc",
        }

        logger.info("GDELT request: query=%r maxrecords=%d timespan=%s", query, max_records, settings.NEWS_TIMESPAN)

        async with httpx.AsyncClient(
            timeout=settings.NEWS_HTTP_TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        ) as client:
            resp = await client.get(settings.GDELT_BASE_URL, params=params)

        if resp.status_code == 429:
            raise RateLimitError(f"GDELT HTTP 429: {resp.text[:200]}")

        resp.raise_for_status()

        body_text = (resp.text or "").strip()
        if not body_text:
            logger.info("GDELT returned empty body for query=%r", query)
            return []

        try:
            payload = resp.json()
        except Exception:
            lowered = body_text.lower()
            if any(hint in lowered for hint in _RATE_LIMIT_HINTS):
                raise RateLimitError(f"GDELT rate-limit text: {body_text[:200]}")
            logger.warning(
                "GDELT returned non-JSON body (HTTP %d): %s",
                resp.status_code,
                body_text[:200],
            )
            return []

        if not isinstance(payload, dict):
            logger.warning("GDELT returned unexpected JSON type: %s", type(payload).__name__)
            return []

        raw_articles = payload.get("articles")
        if not raw_articles or not isinstance(raw_articles, list):
            return []

        seen_titles: set[str] = set()
        seen_urls: set[str] = set()
        items: list[NewsItem] = []

        for art in raw_articles:
            if not isinstance(art, dict):
                continue
            title = str(art.get("title") or "").strip()
            url = str(art.get("url") or "").strip()
            if not title or not url:
                continue

            norm_title = _normalize_title(title)
            if norm_title in seen_titles or url in seen_urls:
                continue
            seen_titles.add(norm_title)
            seen_urls.add(url)

            items.append(
                NewsItem(
                    title=title,
                    source=str(art.get("domain") or "").strip(),
                    url=url,
                    published_at=_parse_seendate(art.get("seendate")),
                    snippet="",
                    country=str(art.get("sourcecountry")).strip()
                    if art.get("sourcecountry")
                    else None,
                )
            )

        # Newest first (items without published_at go last)
        epoch_min = datetime.min.replace(tzinfo=timezone.utc)
        items.sort(key=lambda x: x.published_at or epoch_min, reverse=True)
        return items[:limit]
