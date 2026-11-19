"""
Auth router: endpoints for registration, login, token issue, and current user profile.
"""
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.auth_controller import AuthController
from app.core.dependencies import get_current_user, get_db
from app.models.orm.user import User
from app.models.schemas.auth import Token, UserCreate, UserLogin, UserOut

router = APIRouter()


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description="Creates a new founder account with email, password, and full name.",
)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    """Handle new user registration."""
    return await AuthController.register(user_in=user_in, db=db)


@router.post(
    "/login",
    response_model=Token,
    summary="User login (JSON)",
    description="Authenticate with email and password in JSON body, returns a JWT bearer access token.",
)
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Handle JSON-based login for web frontend and REST clients."""
    return await AuthController.login(login_data=login_data, db=db)


@router.post(
    "/token",
    response_model=Token,
    summary="OAuth2 Password token endpoint",
    description="Form-encoded login endpoint used by OpenAPI / Swagger UI Authorize dialog.",
)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    """OAuth2 password form endpoint for Swagger UI Authorize button."""
    return await AuthController.login_oauth(
        username=form_data.username,
        password=form_data.password,
        db=db,
    )


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get current user profile",
    description="Returns the profile of the authenticated user whose token is in the Authorization header.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserOut:
    """Return authenticated user profile."""
    return await AuthController.get_me(current_user=current_user)
