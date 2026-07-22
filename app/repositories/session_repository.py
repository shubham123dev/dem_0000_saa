"""Repository for server-side user session management and DB-backed token validation."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import DEFAULT_SESSION_TTL_HOURS, generate_session_token, hash_token
from app.db.orm_models import UserSessionORM


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_session(
        self,
        user_id: str,
        ttl_hours: int = DEFAULT_SESSION_TTL_HOURS,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[UserSessionORM, str]:
        """Create and persist a new session record tied to a Test_user1.UserID."""
        raw_token = generate_session_token()
        token_hash = hash_token(raw_token)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=ttl_hours)

        session_record = UserSessionORM(
            id=f"sess_{uuid.uuid4().hex[:16]}",
            user_id=str(user_id),
            session_token_hash=token_hash,
            created_at=now,
            expires_at=expires_at,
            is_revoked=False,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._session.add(session_record)
        await self._session.commit()
        await self._session.refresh(session_record)
        return session_record, raw_token

    async def get_active_session(self, raw_token: str) -> UserSessionORM | None:
        """Fetch active, unexpired session for a given raw token string."""
        token_hash = hash_token(raw_token)
        now = datetime.now(timezone.utc)

        statement = select(UserSessionORM).where(
            UserSessionORM.session_token_hash == token_hash,
            UserSessionORM.is_revoked == False,  # noqa: E712
            UserSessionORM.expires_at > now,
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def revoke_session(self, raw_token: str) -> bool:
        """Revoke an active session by token string."""
        token_hash = hash_token(raw_token)
        statement = (
            update(UserSessionORM)
            .where(UserSessionORM.session_token_hash == token_hash)
            .values(is_revoked=True)
        )
        result = await self._session.execute(statement)
        await self._session.commit()
        return result.rowcount > 0

    async def revoke_all_user_sessions(self, user_id: str) -> int:
        """Revoke all active sessions for a specific UserID in Test_user1."""
        statement = (
            update(UserSessionORM)
            .where(
                UserSessionORM.user_id == str(user_id),
                UserSessionORM.is_revoked == False,  # noqa: E712
            )
            .values(is_revoked=True)
        )
        result = await self._session.execute(statement)
        await self._session.commit()
        return result.rowcount
