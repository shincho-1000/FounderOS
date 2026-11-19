"""
Short-term memory: sliding window of the most recent interactions per business.

Invariant: the collection never holds more than SHORT_TERM_WINDOW documents
for a business. Entries that overflow are deleted and *returned* so the caller
can fold them into the summary tier before they are lost.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings
from app.db.mongo import get_mongo_db
from app.models.schemas.memory import ShortTermEntryOut, serialize_doc

logger = logging.getLogger(__name__)

COLLECTION = "short_term_memory"


def _utc(dt: datetime) -> datetime:
    """Mongo returns naive UTC datetimes; make them explicit."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _to_out(doc: dict) -> ShortTermEntryOut:
    d = serialize_doc(doc)
    d["created_at"] = _utc(d["created_at"])
    return ShortTermEntryOut(**d)


async def add(
    business_id: str,
    question: str,
    answer_summary: str,
    decision_id: Optional[str] = None,
) -> list[dict]:
    """Insert an interaction; return overflow docs (oldest first) already deleted."""
    col = get_mongo_db()[COLLECTION]
    window = settings.SHORT_TERM_WINDOW

    await col.insert_one(
        {
            "business_id": str(business_id),
            "question": question,
            "answer_summary": answer_summary,
            "decision_id": str(decision_id) if decision_id is not None else None,
            "created_at": datetime.now(timezone.utc),
        }
    )

    total = await col.count_documents({"business_id": str(business_id)})
    overflow_count = total - window
    if overflow_count <= 0:
        return []

    # Oldest first; _id breaks ties (Mongo stores datetimes at ms precision).
    overflow = (
        await col.find({"business_id": str(business_id)})
        .sort([("created_at", 1), ("_id", 1)])
        .limit(overflow_count)
        .to_list(length=overflow_count)
    )
    if overflow:
        await col.delete_many({"_id": {"$in": [d["_id"] for d in overflow]}})
    return overflow


async def get_recent(
    business_id: str, limit: Optional[int] = None
) -> list[ShortTermEntryOut]:
    """Newest `limit` entries, returned oldest-first (chronological)."""
    limit = limit or settings.SHORT_TERM_WINDOW
    col = get_mongo_db()[COLLECTION]
    docs = (
        await col.find({"business_id": str(business_id)})
        .sort([("created_at", -1), ("_id", -1)])
        .limit(limit)
        .to_list(length=limit)
    )
    docs.reverse()
    return [_to_out(d) for d in docs]


async def clear(business_id: str) -> int:
    """Delete all short-term entries for a business. Returns deleted count."""
    res = await get_mongo_db()[COLLECTION].delete_many(
        {"business_id": str(business_id)}
    )
    return res.deleted_count
