"""
Business router: create / read / update the current user's business profile.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.business_controller import BusinessController
from app.core.dependencies import get_current_business, get_current_user, get_db
from app.models.orm.business import Business
from app.models.orm.user import User
from app.models.schemas.business import (
    BusinessCreate,
    BusinessOut,
    BusinessUpdate,
)

router = APIRouter()


@router.post(
    "",
    response_model=BusinessOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create my business profile",
)
async def create_business(
    data: BusinessCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BusinessOut:
    return await BusinessController.create(data=data, user=current_user, db=db)


@router.get(
    "",
    response_model=BusinessOut,
    summary="Get my business profile",
)
async def get_business(
    business: Business = Depends(get_current_business),
) -> BusinessOut:
    return await BusinessController.get(business)


@router.put(
    "",
    response_model=BusinessOut,
    summary="Update my business profile (partial)",
)
async def update_business(
    data: BusinessUpdate,
    business: Business = Depends(get_current_business),
    db: AsyncSession = Depends(get_db),
) -> BusinessOut:
    return await BusinessController.update(data=data, business=business, db=db)
