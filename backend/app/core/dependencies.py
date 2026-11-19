"""
FastAPI dependency injection helpers: database session, token parsing, and current user retrieval.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.models.orm.business import Business
from app.models.orm.user import User
from app.services.business_service import BusinessService
from app.services.user_service import UserService
from app.utils.security import decode_access_token

# OAuth2 scheme configured for Swagger UI Authorize button
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token",
    auto_error=True,
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate Bearer token and return authenticated User ORM instance."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = await UserService.get_by_id(db, user_id=user_id)
    if user is None:
        raise credentials_exception

    return user


async def get_current_business(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Business:
    """Return the authenticated user's business, or 404 if not created yet.

    Used by all later phases (memory, news, documents, decisions, insights).
    """
    business = await BusinessService.get_by_user_id(db, current_user.id)
    if business is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No business profile found. Create one with POST /api/v1/business.",
        )
    return business
