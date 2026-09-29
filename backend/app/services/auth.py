import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, hash_password_async, verify_password_async
from app.core.tokens import (
    REFRESH_TTL,
    RESET_TTL,
    create_access_token,
    hash_token,
    new_opaque_token,
)
from app.models import PasswordResetToken, RefreshToken, Role, User

MAX_FAILED = 5
LOCK_FOR = timedelta(minutes=15)
# Verifying against a dummy hash keeps timing similar for unknown emails.
_DUMMY_HASH = hash_password("not-a-real-password")


async def get_role(db: AsyncSession, name: str) -> Role:
    return (await db.execute(select(Role).where(Role.name == name))).scalar_one()


async def issue_tokens(db: AsyncSession, user: User) -> dict[str, str]:
    raw, hashed = new_opaque_token()
    db.add(
        RefreshToken(user_id=user.id, token_hash=hashed, expires_at=datetime.now(UTC) + REFRESH_TTL)
    )
    await db.commit()
    return {
        "access_token": create_access_token(user.id, user.role.name),
        "refresh_token": raw,
    }


async def authenticate(db: AsyncSession, email: str, password: str) -> User:
    user = (await db.execute(select(User).where(User.email == email.lower()))).scalar_one_or_none()
    if user is None:
        await verify_password_async(password, _DUMMY_HASH)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    now = datetime.now(UTC)
    if user.locked_until and user.locked_until > now:
        raise HTTPException(status.HTTP_423_LOCKED, "Account temporarily locked")
    if not user.is_active or not await verify_password_async(password, user.password_hash):
        user.failed_attempts += 1
        if user.failed_attempts >= MAX_FAILED:
            user.locked_until = now + LOCK_FOR
            user.failed_attempts = 0
        await db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    user.failed_attempts = 0
    user.locked_until = None
    return user


async def rotate_refresh(db: AsyncSession, raw: str) -> dict[str, str]:
    token = (
        await db.execute(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)))
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    if token is None or token.expires_at < now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    if token.revoked_at is not None:
        # Reuse of a rotated token signals theft: revoke every session for the user.
        await revoke_all(db, token.user_id)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    token.revoked_at = now
    user = (await db.execute(select(User).where(User.id == token.user_id))).scalar_one()
    if not user.is_active:
        await db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account inactive")
    return await issue_tokens(db, user)


async def revoke_all(db: AsyncSession, user_id: uuid.UUID) -> None:
    now = datetime.now(UTC)
    rows = (
        await db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
            )
        )
    ).scalars()
    for r in rows:
        r.revoked_at = now
    await db.commit()


async def revoke_refresh(db: AsyncSession, raw: str) -> None:
    token = (
        await db.execute(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)))
    ).scalar_one_or_none()
    if token and token.revoked_at is None:
        token.revoked_at = datetime.now(UTC)
        await db.commit()


async def create_reset_token(db: AsyncSession, user: User) -> str:
    raw, hashed = new_opaque_token()
    db.add(
        PasswordResetToken(
            user_id=user.id, token_hash=hashed, expires_at=datetime.now(UTC) + RESET_TTL
        )
    )
    await db.commit()
    return raw


async def consume_reset_token(db: AsyncSession, raw: str, new_password: str) -> None:
    token = (
        await db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(raw))
        )
    ).scalar_one_or_none()
    if token is None or token.used_at is not None or token.expires_at < datetime.now(UTC):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset token")
    user = (await db.execute(select(User).where(User.id == token.user_id))).scalar_one()
    user.password_hash = await hash_password_async(new_password)
    user.failed_attempts = 0
    user.locked_until = None
    token.used_at = datetime.now(UTC)
    await db.commit()
    await revoke_all(db, user.id)
