"""
News service: query building, MongoDB caching (with TTL + stale fallback),
GDELT rate limiting (5.5s spacing), single retry on 429, and 15s hard time cap.

Public API for Phase 7 (Decision Engine):
    items = await news_service.get_news(business_id, industry, question, limit=5)
    # Never raises; returns list[NewsItem].
"""
import asyncio
import hashlib
import logging
import re
import time
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings
from app.db.mongo import get_mongo_db
from app.models.schemas.news import NewsItemOut, NewsResponse
from app.news.base import NewsAdapter, NewsItem, RateLimitError
from app.news.gdelt import GdeltAdapter

logger = logging.getLogger(__name__)

COLLECTION = "news_cache"
TOTAL_TIMEOUT_SECONDS = 15.0
RATE_LIMIT_RETRY_SLEEP = 6.0
MAX_QUERY_LENGTH = 250
MAX_EXTRA_KEYWORDS = 4

_SANITIZE_RE = re.compile(r"[^a-zA-Z0-9\s\-]")
_WHITESPACE_RE = re.compile(r"\s+")

_STOPWORDS = frozenset(
    {
        "the", "and", "for", "that", "this", "with", "from", "your", "our", "are",
        "was", "were", "will", "would", "should", "could", "have", "has", "had",
        "not", "but", "what", "when", "where", "which", "who", "whom", "why", "how",
        "about", "into", "over", "after", "before", "between", "under", "again",
        "more", "most", "some", "such", "only", "same", "than", "too", "very",
        "can", "just", "now", "also", "then", "there", "their", "they", "them",
        "these", "those", "its", "next", "month", "quarter", "year", "week", "day",
        "today", "company", "business", "startup", "need", "want", "make", "take",
    }
)

# Module-level rate limiter & index flag
_rate_lock = asyncio.Lock()
_last_request_ts: float = 0.0
_indexes_ensured: bool = False


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def get_adapter() -> NewsAdapter:
    """Select news adapter from NEWS_PROVIDER; fall back to GdeltAdapter."""
    provider = (settings.NEWS_PROVIDER or "gdelt").strip().lower()
    if provider == "gdelt":
        return GdeltAdapter()
    logger.warning(
        "News provider %r is unsupported or stubbed; falling back to GdeltAdapter.",
        provider,
    )
    return GdeltAdapter()


def _clean_text(text: str) -> str:
    """Strip characters that break GDELT queries (quotes, parens, colons, emoji, etc.)."""
    cleaned = _SANITIZE_RE.sub(" ", text or "")
    # Strip leading/trailing hyphens on tokens to avoid GDELT negation syntax (-word)
    tokens = [tok.strip("-") for tok in _WHITESPACE_RE.split(cleaned) if tok.strip("-")]
    return " ".join(tokens)


def _format_term(term: str) -> Optional[str]:
    """Format a cleaned term for GDELT: phrases in quotes, bare words >= 3 chars."""
    cleaned = _clean_text(term)
    if not cleaned:
        return None
    words = [w for w in cleaned.split(" ") if len(w) >= 3]
    if not words:
        return None
    if len(words) == 1:
        return words[0]
    return f'"{" ".join(words)}"'


def _extract_keywords(
    keywords: Optional[list[str]] = None,
    extra: Optional[str] = None,
) -> list[str]:
    """Extract up to MAX_EXTRA_KEYWORDS lowercase tokens (>=3 chars, no stopwords)."""
    raw_tokens: list[str] = []
    if keywords:
        for kw in keywords:
            raw_tokens.extend(_clean_text(kw).lower().split())
    if extra:
        raw_tokens.extend(_clean_text(extra).lower().split())

    result: list[str] = []
    seen: set[str] = set()
    for tok in raw_tokens:
        if len(tok) < 3 or tok in _STOPWORDS or tok in seen:
            continue
        seen.add(tok)
        result.append(tok)
        if len(result) >= MAX_EXTRA_KEYWORDS:
            break
    return result


def build_query(
    industry: str,
    keywords: Optional[list[str]] = None,
    extra: Optional[str] = None,
) -> str:
    """Build a valid, sanitized GDELT DOC 2.0 query under ~250 characters."""
    terms: list[str] = []
    seen_lower: set[str] = set()

    ind_term = _format_term(industry)
    if ind_term:
        terms.append(ind_term)
        seen_lower.add(ind_term.strip('"').lower())

    for kw in _extract_keywords(keywords=keywords, extra=extra):
        if kw not in seen_lower:
            terms.append(kw)
            seen_lower.add(kw)

    lang = _clean_text(settings.NEWS_LANGUAGE or "english").lower().split()
    lang_suffix = f" sourcelang:{lang[0]}" if lang else ""

    if not terms:
        expr = '("startup" OR "small business")'
        return f"{expr}{lang_suffix}"

    # Fit within MAX_QUERY_LENGTH
    budget = MAX_QUERY_LENGTH - len(lang_suffix) - 2  # reserve for parens
    kept: list[str] = []
    current_len = 0
    for term in terms:
        addition = len(term) if not kept else len(" OR ") + len(term)
        if kept and current_len + addition > budget:
            break
        kept.append(term)
        current_len += addition

    if len(kept) == 1:
        expr = kept[0]
    else:
        expr = "(" + " OR ".join(kept) + ")"

    return f"{expr}{lang_suffix}"


async def _ensure_cache_indexes() -> None:
    """Idempotently create TTL and lookup indexes on news_cache."""
    global _indexes_ensured
    if _indexes_ensured:
        return
    try:
        col = get_mongo_db()[COLLECTION]
        await col.create_index([("business_id", 1), ("query_hash", 1)], unique=True)
        await col.create_index(
            "fetched_at",
            expireAfterSeconds=settings.NEWS_CACHE_TTL_SECONDS * 4,
        )
        _indexes_ensured = True
        logger.info("MongoDB news_cache indexes ensured.")
    except Exception as exc:  # noqa: BLE001 - never break news on index error
        logger.warning("Could not ensure news_cache indexes: %s", exc)


def _query_hash(query: str) -> str:
    return hashlib.sha1(query.encode("utf-8")).hexdigest()


def _serialize_items(items: list[NewsItem]) -> list[dict]:
    return [item.model_dump(mode="json") for item in items]


def _deserialize_items(raw_items: list[dict], limit: int) -> list[NewsItem]:
    parsed: list[NewsItem] = []
    for raw in (raw_items or [])[:limit]:
        try:
            item = NewsItem(**raw)
            if item.published_at is not None:
                item.published_at = _utc(item.published_at)
            parsed.append(item)
        except Exception:  # noqa: BLE001
            continue
    return parsed


async def _read_cache(business_id: str, qhash: str) -> Optional[dict]:
    try:
        await _ensure_cache_indexes()
        col = get_mongo_db()[COLLECTION]
        return await col.find_one(
            {"business_id": str(business_id), "query_hash": qhash}
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("news_cache read failed: %s", exc)
        return None


async def _write_cache(
    business_id: str, qhash: str, query: str, items: list[NewsItem]
) -> None:
    try:
        await _ensure_cache_indexes()
        col = get_mongo_db()[COLLECTION]
        await col.update_one(
            {"business_id": str(business_id), "query_hash": qhash},
            {
                "$set": {
                    "business_id": str(business_id),
                    "query_hash": qhash,
                    "query": query,
                    "items": _serialize_items(items),
                    "fetched_at": datetime.now(timezone.utc),
                }
            },
            upsert=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("news_cache write failed: %s", exc)


async def _acquire_rate_limit() -> None:
    """Ensure at least NEWS_MIN_REQUEST_INTERVAL seconds between GDELT calls."""
    global _last_request_ts
    async with _rate_lock:
        now = time.monotonic()
        if _last_request_ts > 0:
            elapsed = now - _last_request_ts
            wait = settings.NEWS_MIN_REQUEST_INTERVAL - elapsed
            if wait > 0:
                logger.info("Rate limiter sleeping %.2fs before GDELT call", wait)
                await asyncio.sleep(wait)
        _last_request_ts = time.monotonic()


async def _fetch_with_retry(
    adapter: NewsAdapter, query: str, fetch_limit: int
) -> list[NewsItem]:
    """Rate-limited fetch with one 6-second retry on RateLimitError."""
    global _last_request_ts
    await _acquire_rate_limit()
    try:
        return await adapter.fetch(query, limit=fetch_limit)
    except RateLimitError as exc:
        logger.warning(
            "Rate limited by %s (%s); waiting %.1fs and retrying once.",
            adapter.provider_name,
            exc,
            RATE_LIMIT_RETRY_SLEEP,
        )
        await asyncio.sleep(RATE_LIMIT_RETRY_SLEEP)
        async with _rate_lock:
            _last_request_ts = time.monotonic()
        return await adapter.fetch(query, limit=fetch_limit)


async def _fetch_news_internal(
    business_id: str,
    query: str,
    limit: int,
) -> tuple[list[NewsItem], str, bool]:
    """Core logic returning (items, provider_name, cached). Never raises."""
    adapter = get_adapter()
    provider = adapter.provider_name
    qhash = _query_hash(query)

    # 1. Check Mongo cache
    cache_doc = await _read_cache(business_id, qhash)
    if cache_doc and cache_doc.get("fetched_at"):
        fetched_at = _utc(cache_doc["fetched_at"])
        age = (datetime.now(timezone.utc) - fetched_at).total_seconds()
        if age < settings.NEWS_CACHE_TTL_SECONDS:
            cached_items = _deserialize_items(cache_doc.get("items", []), limit)
            return cached_items, provider, True

    # 2. Live fetch with 15s total time cap
    fetch_limit = max(limit, settings.NEWS_MAX_RECORDS)
    try:
        items = await asyncio.wait_for(
            _fetch_with_retry(adapter, query, fetch_limit),
            timeout=TOTAL_TIMEOUT_SECONDS,
        )
        await _write_cache(business_id, qhash, query, items)
        return items[:limit], provider, False
    except Exception as exc:  # noqa: BLE001 - fail-soft by design
        logger.warning(
            "News fetch failed (%s: %s) for query=%r",
            type(exc).__name__,
            exc,
            query,
        )
        if cache_doc and cache_doc.get("items"):
            logger.info("serving stale news for business_id=%s query=%r", business_id, query)
            return _deserialize_items(cache_doc.get("items", []), limit), provider, True
        return [], provider, False


async def get_news(
    business_id: str,
    industry: str,
    question: Optional[str] = None,
    limit: int = 5,
) -> list[NewsItem]:
    """Public API for Phase 7 (Decision Engine). Never raises."""
    try:
        query = build_query(industry=industry, extra=question)
        items, _, _ = await _fetch_news_internal(business_id, query, limit)
        return items
    except Exception:  # noqa: BLE001
        logger.exception("Unexpected error in news_service.get_news")
        return []


async def get_news_response(
    business_id: str,
    industry: str,
    query_override: Optional[str] = None,
    limit: int = 5,
) -> NewsResponse:
    """Controller helper: builds query, fetches news, returns shaped NewsResponse."""
    try:
        if query_override is not None and query_override.strip():
            # Treat explicit user query as the primary phrase/keywords
            query = build_query(industry=query_override.strip())
        else:
            query = build_query(industry=industry)

        items, provider, cached = await _fetch_news_internal(business_id, query, limit)
        out_items = [NewsItemOut(**item.model_dump()) for item in items]
        return NewsResponse(
            query=query,
            provider=provider,
            cached=cached,
            count=len(out_items),
            items=out_items,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Unexpected error in news_service.get_news_response")
        return NewsResponse(
            query=build_query(industry=industry),
            provider=settings.NEWS_PROVIDER or "gdelt",
            cached=False,
            count=0,
            items=[],
        )
