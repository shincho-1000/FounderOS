"""
Motor (async MongoDB) client for MongoDB Atlas.
"""
import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def connect_mongo():
    """Initialize the Motor client and ping MongoDB Atlas. Called at startup."""
    global _client, _db
    _client = AsyncIOMotorClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
    _db = _client[settings.MONGO_DB]
    # Ping MongoDB to verify connection
    await _client.admin.command("ping")
    print(f"MongoDB Atlas connected successfully — DB: {settings.MONGO_DB}")


async def close_mongo():
    """Close the Motor client. Called at shutdown."""
    global _client
    if _client:
        _client.close()
        print("MongoDB connection closed.")


def get_mongo_db() -> AsyncIOMotorDatabase:
    """Return the active MongoDB database."""
    if _db is None:
        raise RuntimeError("MongoDB not initialized — call connect_mongo() first")
    return _db


async def ensure_indexes() -> None:
    """Create Phase 4 memory indexes. Idempotent and never raises."""
    try:
        db = get_mongo_db()
        await db.short_term_memory.create_index(
            [("business_id", 1), ("created_at", -1)]
        )
        await db.long_term_memory.create_index(
            [("business_id", 1), ("importance", -1), ("created_at", -1)]
        )
        await db.memory_summary.create_index("business_id", unique=True)
        logger.info("MongoDB memory indexes ensured.")
    except Exception as exc:  # noqa: BLE001 - startup must not fail on indexes
        logger.warning("Could not create MongoDB memory indexes: %s", exc)
