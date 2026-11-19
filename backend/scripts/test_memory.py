"""
Phase 4 memory test: 14 interactions through memory_service with
SHORT_TERM_WINDOW=10 against the real MongoDB.

Verifies: short-term holds exactly the newest 10, the rolling summary exists,
mentions the 4 overflowed interactions, and interactions_summarized == 4.

Usage (from backend/):
    venv/bin/python scripts/test_memory.py              # use configured key
    venv/bin/python scripts/test_memory.py --no-key     # GEMINI_API_KEY unset
    venv/bin/python scripts/test_memory.py --fake-key   # invalid key -> Gemini fails -> fallback
    venv/bin/python scripts/test_memory.py --mock-gemini  # stub Gemini call, test the wiring
"""
import asyncio
import logging
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402
from app.db import mongo  # noqa: E402
from app.memory import summary  # noqa: E402
from app.services import memory_service  # noqa: E402

WINDOW = 10
TOTAL = 14


async def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="  [log] %(levelname)s %(message)s")
    mode = "configured key"
    if "--no-key" in sys.argv:
        settings.GEMINI_API_KEY = ""
        mode = "GEMINI_API_KEY unset"
    elif "--fake-key" in sys.argv:
        settings.GEMINI_API_KEY = "AIza-fake-invalid-key-for-testing"
        mode = "invalid key (real Gemini call fails)"
    elif "--mock-gemini" in sys.argv:
        async def fake(existing, entries):
            return "MOCK SUMMARY: " + "; ".join(e["question"][:3] for e in entries)
        summary._summarize_with_gemini = fake
        settings.GEMINI_API_KEY = "AIza-mock"
        mode = "mocked Gemini"

    settings.SHORT_TERM_WINDOW = WINDOW
    print(f"Mode: {mode} | window={WINDOW} | key_present={summary._has_gemini_key()}")

    await mongo.connect_mongo()
    await mongo.ensure_indexes()
    bid = f"test-memory-{uuid.uuid4()}"
    db = mongo.get_mongo_db()
    failures: list[str] = []

    def check(cond: bool, msg: str) -> None:
        print(("  PASS " if cond else "  FAIL ") + msg)
        if not cond:
            failures.append(msg)

    try:
        for i in range(1, TOTAL + 1):
            await memory_service.add_interaction(
                bid, f"Q{i:02d} should we do thing {i}?", f"A{i:02d} yes do thing {i}"
            )
            n = await db.short_term_memory.count_documents({"business_id": bid})
            if n > WINDOW:
                failures.append(f"window exceeded after insert {i}: {n}")

        docs = await db.short_term_memory.find({"business_id": bid}).to_list(None)
        questions = sorted(d["question"][:3] for d in docs)
        expected = [f"Q{i:02d}" for i in range(TOTAL - WINDOW + 1, TOTAL + 1)]
        check(len(docs) == WINDOW, f"short-term holds exactly {WINDOW} (got {len(docs)})")
        check(questions == expected, f"short-term holds the newest ({expected[0]}..{expected[-1]})")

        s = await summary.get(bid)
        check(bool(s.summary), "memory_summary exists and is non-empty")
        check(s.interactions_summarized == TOTAL - WINDOW,
              f"interactions_summarized == {TOTAL - WINDOW} (got {s.interactions_summarized})")
        check(len(s.summary) <= settings.SUMMARY_MAX_CHARS, "summary within SUMMARY_MAX_CHARS")
        count = await db.memory_summary.count_documents({"business_id": bid})
        check(count == 1, f"exactly one summary doc per business (got {count})")
        if "--mock-gemini" in sys.argv:
            check(s.summary.startswith("MOCK SUMMARY"), "summary came from the (mocked) Gemini path")
        else:
            overflowed = [f"Q{i:02d}" for i in range(1, TOTAL - WINDOW + 1)]
            check(all(q in s.summary for q in overflowed),
                  f"summary mentions the overflowed interactions {overflowed}")
        print("  Summary:\n    " + s.summary.replace("\n", "\n    "))

        ctx = await memory_service.get_context(bid)
        check(len(ctx.short_term) == WINDOW and ctx.summary != "", "get_context returns short-term + summary")
        check([e.question[:3] for e in ctx.short_term] == expected, "short-term is chronological (oldest first)")
    finally:
        for col in ("short_term_memory", "long_term_memory", "memory_summary"):
            await db[col].delete_many({"business_id": bid})
        await mongo.close_mongo()

    print("\nRESULT:", "PASS" if not failures else f"FAIL {failures}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
