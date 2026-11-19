"""
Business service: database operations for the Business model.
One business per user (hackathon scope).
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm.business import Business
from app.models.schemas.business import BusinessCreate, BusinessUpdate


class BusinessService:
    @staticmethod
    async def get_by_user_id(db: AsyncSession, user_id: str) -> Optional[Business]:
        result = await db.execute(
            select(Business).where(Business.user_id == user_id).limit(1)
        )
        return result.scalars().first()

    @staticmethod
    async def create(
        db: AsyncSession, user_id: str, data: BusinessCreate
    ) -> Business:
        business = Business(user_id=user_id, **data.model_dump())
        db.add(business)
        await db.commit()
        await db.refresh(business)
        return business

    @staticmethod
    async def update(
        db: AsyncSession, business: Business, data: BusinessUpdate
    ) -> Business:
        # Only apply fields the client explicitly sent.
        changes = data.model_dump(exclude_unset=True)
        for field, value in changes.items():
            # name/industry are NOT NULL: ignore explicit nulls for them.
            if value is None and field in ("name", "industry"):
                continue
            setattr(business, field, value)
        db.add(business)
        await db.commit()
        await db.refresh(business)
        return business
