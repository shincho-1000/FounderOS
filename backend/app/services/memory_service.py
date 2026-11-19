"""
Memory service: the public API other phases (notably the Phase 7 decision engine)
use to read and write memory.

  get_context()          -> read all three tiers (never raises)
  add_interaction()      -> write short-term, fold overflow into summary (never raises)
  record_decision()      -> convenience wrapper for Phase 7 (never raises)
  add_long_term_entry()  -> write a durable fact (raises on Mongo failure)
  format_for_prompt()    -> three ready-to-embed strings
"""
import asyncio
import logging
from typing import Awaitable, Optional, TypeVar

from app.memory import long_term, short_term, summary
from app.models.schemas.memory import (
    LongTermEntryOut,
    MemoryCategory,
    MemoryContext,
    MemorySummaryOut,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")

ANSWER_SUMMARY_MAX_CHARS = 300
DECISION_TEXT_MAX_CHARS = 300

# Serialize writes per business so overflow/fold-in cannot interleave.
_locks: dict[str, asyncio.Lock] = {}


def _lock_for(business_id: str) -> asyncio.Lock:
    return _locks.setdefault(str(business_id), asyncio.Lock())


async def _safe(coro: Awaitable[T], default: T, label: str) -> T:
    try:
        return await coro
    except Exception as exc:  # noqa: BLE001 - memory must never break callers
        logger.warning("Memory read failed for %s: %s: %s", label, type(exc).__name__, exc)
        return default


def _truncate(text: str, limit: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


async def get_context(business_id: str) -> MemoryContext:
    """Fetch all three tiers concurrently; each tier fails soft. Never raises."""
    try:
        recent, summ, top = await asyncio.gather(
            _safe(short_term.get_recent(business_id), [], "short_term"),
            _safe(summary.get(business_id), MemorySummaryOut(), "summary"),
            _safe(long_term.get_top_k(business_id), [], "long_term"),
        )
        return MemoryContext(short_term=recent, summary=summ.summary, long_term=top)
    except Exception:  # noqa: BLE001
        logger.exception("Unexpected failure building memory context")
        return MemoryContext()


async def add_interaction(
    business_id: str,
    question: str,
    answer_summary: str,
    decision_id: Optional[str] = None,
) -> None:
    """Record an interaction; overflow is folded into the summary. Never raises."""
    try:
        async with _lock_for(business_id):
            overflow = await short_term.add(
                business_id, question, answer_summary, decision_id
            )
            if overflow:
                await summary.fold_in(business_id, overflow)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to record interaction in short-term memory")


async def add_long_term_entry(
    business_id: str,
    category: MemoryCategory | str,
    content: str,
    importance: int = 3,
) -> LongTermEntryOut:
    """Write a durable fact (deduplicated). Raises on storage failure."""
    return await long_term.add(business_id, category, content, importance)


async def record_decision(
    business_id: str,
    question: str,
    recommendation: str,
    decision_id: Optional[str],
    important: bool = False,
    importance: int = 3,
) -> None:
    """Called by Phase 7 after each decision. Never raises."""
    try:
        await add_interaction(
            business_id,
            question,
            _truncate(recommendation, ANSWER_SUMMARY_MAX_CHARS),
            decision_id,
        )
        if important:
            await add_long_term_entry(
                business_id,
                MemoryCategory.past_decision,
                f"Decided: {question.strip()} -> "
                f"{_truncate(recommendation, DECISION_TEXT_MAX_CHARS)}",
                importance,
            )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to record decision in memory")


async def format_for_prompt(context: MemoryContext) -> dict[str, str]:
    """Ready-to-embed strings for the [LONG-TERM MEMORY], [HISTORY SUMMARY]
    and [RECENT CONTEXT] prompt sections. Empty string when a tier is empty."""
    long_term_text = "\n".join(
        f"- [{e.category.value}, importance {e.importance}] {e.content}"
        for e in context.long_term
    )
    recent_text = "\n".join(
        f"- Q: {e.question}\n  A: {e.answer_summary}" for e in context.short_term
    )
    return {
        "long_term_text": long_term_text,
        "summary_text": context.summary or "",
        "recent_text": recent_text,
    }
