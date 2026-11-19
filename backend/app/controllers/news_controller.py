"""
News controller: HTTP orchestration for GET /news.
Ensures the user has a business profile (400 if missing) and delegates to news_service.
"""
from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_business, get_current_user, get_db
from app.models.orm.business import Business
from app.models.orm.user import User
from app.models.schemas.news import NewsResponse
from app.services import news_service


class NewsController:
    @staticmethod
    async def require_business(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> Business:
        """Dependency: return caller's business, or 400 if none exists yet."""
        try:
            return await get_current_business(current_user=current_user, db=db)
        except HTTPException as exc:
            if exc.status_code == status.HTTP_404_NOT_FOUND:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Create a business profile first",
                ) from exc
            raise

    @staticmethod
    async def get_news(
        business: Business,
        query: Optional[str],
        limit: int,
    ) -> NewsResponse:
        """Always returns 200 with NewsResponse (items=[] if upstream fails)."""
        return await news_service.get_news_response(
            business_id=business.id,
            industry=business.industry,
            query_override=query,
            limit=limit,
        )
