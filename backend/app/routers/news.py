"""
News router: declares GET /news route and dependencies only; logic lives in controller.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.controllers.news_controller import NewsController
from app.models.orm.business import Business
from app.models.schemas.news import NewsResponse

router = APIRouter()


@router.get(
    "",
    response_model=NewsResponse,
    summary="Fetch industry or custom-query news headlines",
)
async def get_news(
    query: Optional[str] = Query(
        default=None,
        description="Optional custom search query. Omit to use the business industry.",
    ),
    limit: int = Query(default=5, ge=1, le=20),
    business: Business = Depends(NewsController.require_business),
) -> NewsResponse:
    return await NewsController.get_news(business=business, query=query, limit=limit)
