"""Authentication and Session Management API Routes.

Handles HTTP-Only cookie issuance, user verification against Test_user1,
session creation, and logout session revocation.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from pydantic import BaseModel, EmailStr

from app.api.dependencies import (
    UserDep,
    UserDirectoryDep,
    get_session_repository,
    get_user_repository,
)
from app.core.config import get_settings
from app.core.errors import UnauthenticatedError, UserDisabledError
from app.core.security import SESSION_COOKIE_NAME, clear_session_cookie, set_session_cookie
from app.domain.enums import UserStatus
from app.domain.models import User
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str | None = None
    user_id: str | None = None
    password: str | None = None


class UserProfileResponse(BaseModel):
    id: str
    display_name: str
    email: str
    status: str
    created_at: str | None = None
    entitlements: dict = {}
    token: str | None = None


def _format_date(val: Any) -> str | None:
    if val is None:
        return None
    if isinstance(val, str):
        return val
    if hasattr(val, "isoformat") and callable(val.isoformat):
        return val.isoformat()
    return str(val)


def _user_to_response(user: User, token: str | None = None) -> UserProfileResponse:
    return UserProfileResponse(
        id=user.id,
        display_name=user.display_name,
        email=user.email,
        status=user.status.value,
        created_at=_format_date(user.created_at),
        entitlements=getattr(user, "extra_fields", {}),
        token=token,
    )


@router.post("/login", response_model=UserProfileResponse)
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    user_directory: UserDirectoryDep,
    session_repo: Annotated[SessionRepository, Depends(get_session_repository)],
) -> UserProfileResponse:
    """Authenticate user against Test_user1 identity directory and issue HTTP-only cookie."""
    user: User | None = None

    if body.user_id:
        user = await user_directory.get_by_id(body.user_id)
    elif body.email:
        if body.password and hasattr(user_directory, "get_by_email_and_password"):
            user = await user_directory.get_by_email_and_password(body.email, body.password)
        else:
            user = await user_directory.get_by_email(body.email)
    else:
        raise UnauthenticatedError("Either email or user_id must be provided for login")

    if user is None:
        raise UnauthenticatedError("User not found in Test_user1 directory")

    if not user.is_active or user.status != UserStatus.ACTIVE:
        raise UserDisabledError("User account is disabled or inactive")

    # Capture IP address and User Agent for audit logging
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    # Create server-side session in database
    session_record, raw_token = await session_repo.create_session(
        user_id=user.id,
        ip_address=client_ip,
        user_agent=user_agent,
    )

    # Set HTTP-only session cookie
    settings = get_settings()
    set_session_cookie(response, raw_token, secure=settings.session_cookie_secure)

    return _user_to_response(user, raw_token)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    response: Response,
    session_repo: Annotated[SessionRepository, Depends(get_session_repository)],
    workplace_session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> dict[str, str]:
    """Revoke current active session and clear HTTP-only cookie."""
    token = workplace_session_token
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if token:
        await session_repo.revoke_session(token)

    clear_session_cookie(response)
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(user: UserDep) -> UserProfileResponse:
    """Return currently authenticated user profile verified live from Test_user1."""
    return _user_to_response(user)
