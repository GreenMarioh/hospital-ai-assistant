from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.ratelimit import AUTH_LIMIT, limiter
from app.core.security import hash_password_async
from app.models import Patient, User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenPair,
    UserOut,
)
from app.services import auth as svc
from app.services.email import send_email

router = APIRouter(prefix="/api/auth", tags=["auth"])


def user_out(u: User) -> UserOut:
    return UserOut(
        id=u.id, email=u.email, full_name=u.full_name, role=u.role.name, is_active=u.is_active
    )


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
@limiter.limit(AUTH_LIMIT)
async def register(request: Request, body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    email = body.email.lower()
    if (await db.execute(select(User).where(User.email == email))).scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    role = await svc.get_role(db, "patient")
    user = User(
        email=email,
        password_hash=await hash_password_async(body.password),
        full_name=f"{body.first_name} {body.last_name}",
        role_id=role.id,
    )
    db.add(user)
    await db.flush()
    db.add(
        Patient(
            user_id=user.id,
            first_name=body.first_name,
            last_name=body.last_name,
            date_of_birth=body.date_of_birth,
            phone=body.phone,
            email=email,
        )
    )
    await db.commit()
    await db.refresh(user)
    return await svc.issue_tokens(db, user)


@router.post("/login", response_model=TokenPair)
@limiter.limit(AUTH_LIMIT)
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await svc.authenticate(db, body.email, body.password)
    return await svc.issue_tokens(db, user)


@router.post("/refresh", response_model=TokenPair)
@limiter.limit(AUTH_LIMIT)
async def refresh(request: Request, body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    return await svc.rotate_refresh(db, body.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> Response:
    await svc.revoke_refresh(db, body.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(AUTH_LIMIT)
async def forgot_password(
    request: Request, body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    user = (
        await db.execute(select(User).where(User.email == body.email.lower()))
    ).scalar_one_or_none()
    if user and user.is_active:
        raw = await svc.create_reset_token(db, user)
        send_email(user.email, "Password reset", f"Use this token to reset your password: {raw}")
    # Same response either way: never reveal whether an account exists.
    return {"detail": "If the account exists, a reset email has been sent."}


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(AUTH_LIMIT)
async def reset_password(
    request: Request, body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)
) -> Response:
    await svc.consume_reset_token(db, body.token, body.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(AUTH_LIMIT)
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    await svc.change_password(db, user, body.current_password, body.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> UserOut:
    return user_out(user)
