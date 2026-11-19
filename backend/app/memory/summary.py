"""
Summary memory: a rolling, compressed history of interactions that fell out of
the short-term window. Exactly one document per business.

fold_in() is fail-soft: if Gemini is unavailable it falls back to a
deterministic summary and never raises to the caller.
"""
import asyncio
import logging
from datetime import datetime, timezone

from app.core.config import settings
from app.db.mongo import get_mongo_db
from app.models.schemas.memory import MemorySummaryOut

logger = logging.getLogger(__name__)

COLLECTION = "memory_summary"
GEMINI_TIMEOUT_SECONDS = 10


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _has_gemini_key() -> bool:
    key = (settings.GEMINI_API_KEY or "").strip()
    return bool(key) and not key.lower().startswith("your-")


def _format_entries(entries: list[dict]) -> str:
    return "\n".join(
        f"- Q: {e.get('question', '')}\n  A: {e.get('answer_summary', '')}"
        for e in entries
    )


async def _summarize_with_gemini(existing: str, entries: list[dict]) -> str:
    """Ask Gemini for an updated rolling summary. Raises on any failure.

    Isolated on purpose so Phase 7's gemini_service can replace it.
    """
    from google import genai  # local import: keeps module import cheap

    prompt = (
        "You maintain the rolling memory of a startup-advisor AI.\n"
        "Update the EXISTING SUMMARY so it also covers the NEW INTERACTIONS.\n"
        "Rules:\n"
        f"- Maximum {settings.SUMMARY_MAX_CHARS} characters.\n"
        "- Preserve key decisions, numbers, constraints and outcomes.\n"
        "- Drop chit-chat and repetition.\n"
        "- Never invent facts that are not in the input.\n"
        "- Plain text only, no markdown, no headings.\n\n"
        f"EXISTING SUMMARY:\n{existing or '(none)'}\n\n"
        f"NEW INTERACTIONS:\n{_format_entries(entries)}\n\n"
        "UPDATED SUMMARY:"
    )
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = await asyncio.wait_for(
        client.aio.models.generate_content(
            model=settings.GEMINI_MODEL, contents=prompt
        ),
        timeout=GEMINI_TIMEOUT_SECONDS,
    )
    text = (response.text or "").strip()
    if not text:
        raise ValueError("Gemini returned an empty summary")
    return text


def _fallback_summary(existing: str, entries: list[dict]) -> str:
    """Deterministic summary: one line per overflow entry, keep the tail."""
    lines = [
        f"Q: {str(e.get('question', ''))[:120]} -> "
        f"{str(e.get('answer_summary', ''))[:160]}"
        for e in entries
    ]
    combined = "\n".join(([existing] if existing else []) + lines)
    return _cap_tail(combined)


def _cap_tail(text: str) -> str:
    """Keep only the last SUMMARY_MAX_CHARS characters (drop a partial first line)."""
    limit = settings.SUMMARY_MAX_CHARS
    if len(text) <= limit:
        return text
    tail = text[-limit:]
    if text[-limit - 1] != "\n":  # we cut mid-line: drop the partial line
        newline = tail.find("\n")
        if newline != -1 and newline + 1 < len(tail):
            tail = tail[newline + 1:]
    return tail


def _cap_head(text: str) -> str:
    """Hard cap for LLM output."""
    limit = settings.SUMMARY_MAX_CHARS
    return text if len(text) <= limit else text[:limit].rstrip()


async def get(business_id: str) -> MemorySummaryOut:
    doc = await get_mongo_db()[COLLECTION].find_one(
        {"business_id": str(business_id)}
    )
    if not doc:
        return MemorySummaryOut()
    return MemorySummaryOut(
        summary=doc.get("summary", ""),
        interactions_summarized=doc.get("interactions_summarized", 0),
        updated_at=_utc(doc.get("updated_at")),
    )


async def fold_in(business_id: str, overflow_entries: list[dict]) -> None:
    """Fold overflowed interactions into the single rolling summary. Never raises."""
    if not overflow_entries:
        return
    try:
        col = get_mongo_db()[COLLECTION]
        current = await col.find_one({"business_id": str(business_id)})
        existing = (current or {}).get("summary", "")

        new_summary = None
        if _has_gemini_key():
            try:
                new_summary = _cap_head(
                    await _summarize_with_gemini(existing, overflow_entries)
                )
            except Exception as exc:  # noqa: BLE001 - fail soft by design
                logger.warning(
                    "Gemini summarization failed (%s: %s); using fallback summary.",
                    type(exc).__name__, exc,
                )
        else:
            logger.warning(
                "GEMINI_API_KEY not configured; using deterministic fallback summary."
            )
        if new_summary is None:
            new_summary = _fallback_summary(existing, overflow_entries)

        await col.update_one(
            {"business_id": str(business_id)},
            {
                "$set": {
                    "summary": new_summary,
                    "updated_at": datetime.now(timezone.utc),
                },
                "$inc": {"interactions_summarized": len(overflow_entries)},
            },
            upsert=True,
        )
    except Exception:  # noqa: BLE001 - never raise to the caller
        logger.exception("Failed to fold overflow into summary memory")


async def reset(business_id: str) -> None:
    await get_mongo_db()[COLLECTION].delete_one({"business_id": str(business_id)})
