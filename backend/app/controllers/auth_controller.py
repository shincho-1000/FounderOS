"""
Auth controller: orchestrates registration, login, and user profile retrieval.
"""
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.orm.user import User
from app.models.schemas.auth import UserCreate, UserLogin, Token, UserOut
from app.services.user_service import UserService
from app.utils.security import create_access_token


class AuthController:
    @staticmethod
    async def register(user_in: UserCreate, db: AsyncSession) -> UserOut:
        """Register a new user account."""
        existing = await UserService.get_by_email(db, user_in.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        user = await UserService.create(db, user_in)
        return UserOut.model_validate(user)

    @staticmethod
    async def login(login_data: UserLogin, db: AsyncSession) -> Token:
        """Authenticate user by email & password and return a JWT access token."""
        user = await UserService.authenticate(
            db, email=login_data.email, password=login_data.password
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = create_access_token(data={"sub": user.id, "email": user.email})
        return Token(access_token=token, token_type="bearer")

    @staticmethod
    async def login_oauth(username: str, password: str, db: AsyncSession) -> Token:
        """Authenticate via OAuth2 Password form (Swagger UI Authorize button)."""
        user = await UserService.authenticate(db, email=username, password=password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = create_access_token(data={"sub": user.id, "email": user.email})
        return Token(access_token=token, token_type="bearer")

    @staticmethod
    async def get_me(current_user: User) -> UserOut:
        """Return the profile of the currently authenticated user."""
        return UserOut.model_validate(current_user)
