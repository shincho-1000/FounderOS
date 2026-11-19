"""
Phase 5 quick test script: calls news_service.get_news directly for a sample
industry and prints count, first 3 titles, and elapsed time.

Usage (from backend/):
    venv/bin/python scripts/test_news.py
    venv/bin/python scripts/test_news.py "electric vehicles"
"""
import asyncio
import logging
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import mongo  # noqa: E402
from app.services import news_service  # noqa: E402


async def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="  [log] %(levelname)s %(name)s: %(message)s"
    )
    industry = sys.argv[1] if len(sys.argv) > 1 else "artificial intelligence"
    business_id = f"test-news-{uuid.uuid4()}"

    await mongo.connect_mongo()
    try:
        t0 = time.perf_counter()
        items = await news_service.get_news(
            business_id=business_id,
            industry=industry,
            limit=5,
        )
        elapsed = time.perf_counter() - t0
        print(f"\nIndustry: {industry!r}")
        print(f"Count:    {len(items)}")
        print(f"Elapsed:  {elapsed:.2f}s")
        print("First 3 titles:")
        for idx, item in enumerate(items[:3], start=1):
            print(f"  {idx}. [{item.source}] {item.title} ({item.published_at})")

        # Clean up test cache entry
        db = mongo.get_mongo_db()
        await db.news_cache.delete_many({"business_id": business_id})
        return 0 if len(items) > 0 else 1
    finally:
        await mongo.close_mongo()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
