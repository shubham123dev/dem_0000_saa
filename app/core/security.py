"""Security & Cookie Utilities for Workplace Agent.

Provides HTTP-only cookie configuration, cryptographic session token hashing,
and secure session management boundaries.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Response

SESSION_COOKIE_NAME = "workplace_session_token"
DEFAULT_SESSION_TTL_HOURS = 24


def generate_session_token() -> str:
    """Generate a high-entropy cryptographically secure random session token."""
    return f"wpt_{secrets.token_urlsafe(32)}"


def hash_token(token: str) -> str:
    """Hash session token using SHA-256 before persistence or DB lookup."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def set_session_cookie(
    response: Response,
    session_token: str,
    ttl_hours: int = DEFAULT_SESSION_TTL_HOURS,
    secure: bool = False,
    same_site: str = "lax",
) -> None:
    """Attach an HTTP-only, Secure, SameSite cookie to the outgoing HTTP response."""
    max_age = ttl_hours * 3600
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        max_age=max_age,
        expires=max_age,
        path="/",
        domain=None,
        secure=secure,
        httponly=True,
        samesite=same_site,
    )


def clear_session_cookie(response: Response) -> None:
    """Clear the session cookie from the client browser."""
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
    )
