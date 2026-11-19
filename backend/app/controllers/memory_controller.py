"""
Memory controller: HTTP-level orchestration for the memory endpoints.
Translates storage failures into HTTP errors and delegates to memory_service /
the memory modules.
"""
import logging
from contextlib import contextmanager
from typing import Optional

from fastapi import Depends, HTTPException, status
from pymongo.errors import PyMongoError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_business, get_current_user, get_db
from app.memory import long_term, short_term, summary
from app.models.orm.user import User
from app.models.schemas.memory import (
    LongTermEntryCreate,
    LongTermEntryOut,
    MemoryCategory,
    MemoryContext,
    MemorySummaryOut,
    ShortTermEntryOut,
)
from app.services import memory_service

logger = logging.getLogger(__name__)


@contextmanager
def _mongo_errors():
    """Map MongoDB failures to a 503 with a clear message."""
    try:
        yield
    except HTTPException:
        raise
    except (PyMongoError, RuntimeError) as exc:
        logger.error("MongoDB error in memory endpoint: %s: %s", type(exc).__name__, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Memory store (MongoDB) is temporarily unavailable. Please try again.",
        ) from exc


class MemoryController:
    @staticmethod
    async def require_business_id(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> str:
        """Dependency: the caller's business id, or 400 if no business exists yet."""
        try:
            business = await get_current_business(current_user=current_user, db=db)
        except HTTPException as exc:
            if exc.status_code == status.HTTP_404_NOT_FOUND:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Create a business profile first",
                ) from exc
            raise
        return business.id

    @staticmethod
    async def get_short_term(business_id: str) -> list[ShortTermEntryOut]:
        with _mongo_errors():
            return await short_term.get_recent(business_id)

    @staticmethod
    async def get_summary(business_id: str) -> MemorySummaryOut:
        with _mongo_errors():
            return await summary.get(business_id)

    @staticmethod
    async def list_long_term(
        business_id: str, category: Optional[MemoryCategory]
    ) -> list[LongTermEntryOut]:
        with _mongo_errors():
            return await long_term.list_all(business_id, category)

    @staticmethod
    async def add_long_term(
        business_id: str, data: LongTermEntryCreate
    ) -> LongTermEntryOut:
        with _mongo_errors():
            return await memory_service.add_long_term_entry(
                business_id, data.category, data.content, data.importance
            )

    @staticmethod
    async def delete_long_term(business_id: str, entry_id: str) -> None:
        with _mongo_errors():
            deleted = await long_term.delete(business_id, entry_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Long-term memory entry not found",
            )

    @staticmethod
    async def get_context(business_id: str) -> MemoryContext:
        # memory_service.get_context is fail-soft and never raises.
        return await memory_service.get_context(business_id)

    @staticmethod
    async def reset_conversation(business_id: str) -> None:
        """Clear short-term memory and the rolling summary (long-term is kept)."""
        with _mongo_errors():
            await short_term.clear(business_id)
            await summary.reset(business_id)
