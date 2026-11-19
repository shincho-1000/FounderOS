"""
Motor (async MongoDB) client for MongoDB Atlas.
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

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
