"""
Long-term memory: durable facts (goals, constraints, past decisions, ...) per business.
Retrieval is a simple importance + recency score; no vector search.
"""
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId

from app.core.config import settings
from app.db.mongo import get_mongo_db
from app.models.schemas.memory import (
    LongTermEntryOut,
    MemoryCategory,
    serialize_doc,
)

logger = logging.getLogger(__name__)

COLLECTION = "long_term_memory"
CANDIDATE_LIMIT = 100
RECENCY_MAX_BONUS = 2.0
RECENCY_DECAY_DAYS = 90


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _to_out(doc: dict) -> LongTermEntryOut:
    d = serialize_doc(doc)
    d["created_at"] = _utc(d["created_at"])
    d["updated_at"] = _utc(d.get("updated_at") or d["created_at"])
    return LongTermEntryOut(**d)


def _category_value(category) -> str:
    return category.value if isinstance(category, MemoryCategory) else str(category)


async def add(
    business_id: str,
    category: MemoryCategory | str,
    content: str,
    importance: int = 3,
) -> LongTermEntryOut:
    """Insert an entry, or merge into an existing near-duplicate."""
    col = get_mongo_db()[COLLECTION]
    cat = _category_value(category)
    content = content.strip()
    normalized = content.lower()
    now = datetime.now(timezone.utc)

    # Same business + category + identical normalized (lowercased/trimmed) content.
    existing = await col.find_one(
        {
            "business_id": str(business_id),
            "category": cat,
            "content": {
                "$regex": rf"^\s*{re.escape(normalized)}\s*$",
                "$options": "i",
            },
        }
    )
    if existing:
        new_importance = max(existing.get("importance", 1), importance)
        await col.update_one(
            {"_id": existing["_id"]},
            {"$set": {"importance": new_importance, "updated_at": now}},
        )
        existing["importance"] = new_importance
        existing["updated_at"] = now
        return _to_out(existing)

    doc = {
        "business_id": str(business_id),
        "category": cat,
        "content": content,
        "importance": importance,
        "created_at": now,
        "updated_at": now,
    }
    result = await col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_out(doc)


async def list_all(
    business_id: str, category: Optional[MemoryCategory | str] = None
) -> list[LongTermEntryOut]:
    """All entries for a business, newest first, optionally filtered by category."""
    query: dict = {"business_id": str(business_id)}
    if category is not None:
        query["category"] = _category_value(category)
    docs = (
        await get_mongo_db()[COLLECTION]
        .find(query)
        .sort([("created_at", -1), ("_id", -1)])
        .to_list(length=None)
    )
    return [_to_out(d) for d in docs]


def _score(doc: dict, now: datetime) -> float:
    age_days = max(0.0, (now - _utc(doc["created_at"])).total_seconds() / 86400)
    recency = max(0.0, RECENCY_MAX_BONUS * (1 - age_days / RECENCY_DECAY_DAYS))
    return doc.get("importance", 1) * 2 + recency


async def get_top_k(
    business_id: str, k: Optional[int] = None
) -> list[LongTermEntryOut]:
    """Top-k entries by score = importance*2 + recency bonus (2.0 -> 0 over 90 days)."""
    k = k or settings.LONG_TERM_TOP_K
    candidates = (
        await get_mongo_db()[COLLECTION]
        .find({"business_id": str(business_id)})
        .sort([("importance", -1), ("created_at", -1)])
        .limit(CANDIDATE_LIMIT)
        .to_list(length=CANDIDATE_LIMIT)
    )
    now = datetime.now(timezone.utc)
    candidates.sort(key=lambda d: _score(d, now), reverse=True)
    return [_to_out(d) for d in candidates[:k]]


async def delete(business_id: str, entry_id: str) -> bool:
    """Delete one entry. Scoped to the business so other tenants' ids never match."""
    if not ObjectId.is_valid(entry_id):
        return False
    try:
        oid = ObjectId(entry_id)
    except (InvalidId, TypeError):
        return False
    res = await get_mongo_db()[COLLECTION].delete_one(
        {"_id": oid, "business_id": str(business_id)}
    )
    return res.deleted_count == 1
