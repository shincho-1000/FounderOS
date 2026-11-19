"""
Business controller: orchestrates business profile create / read / update.
"""
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm.business import Business
from app.models.orm.user import User
from app.models.schemas.business import (
    BusinessCreate,
    BusinessOut,
    BusinessUpdate,
)
from app.services.business_service import BusinessService


class BusinessController:
    @staticmethod
    async def create(
        data: BusinessCreate, user: User, db: AsyncSession
    ) -> BusinessOut:
        existing = await BusinessService.get_by_user_id(db, user.id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Business profile already exists. Use PUT /business to update it.",
            )
        business = await BusinessService.create(db, user.id, data)
        return BusinessOut.model_validate(business)

    @staticmethod
    async def get(business: Business) -> BusinessOut:
        return BusinessOut.model_validate(business)

    @staticmethod
    async def update(
        data: BusinessUpdate, business: Business, db: AsyncSession
    ) -> BusinessOut:
        if not data.model_dump(exclude_unset=True):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No fields provided to update.",
            )
        updated = await BusinessService.update(db, business, data)
        return BusinessOut.model_validate(updated)
