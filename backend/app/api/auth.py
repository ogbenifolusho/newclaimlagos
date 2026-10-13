"""
Authentication – JWT + password hashing. MFA hook ready for later.
"""

from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token
from app.db.session import get_db
from app.models.user import User, Role

router = APIRouter()


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    roles: list[str]
    is_active: bool

    class Config:
        from_attributes = True


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str | None = None


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()
    if not user or not user.hashed_password or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    access = create_access_token(str(user.id))
    refresh = create_refresh_token(str(user.id))
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/register", response_model=UserOut, status_code=201)
async def register(
    payload: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Public registration creates a basic user. Role assignment is admin-only."""
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        phone=payload.phone,
        hashed_password=get_password_hash(payload.password),
        is_active=True,
        is_verified=False,
    )
    role_result = await db.execute(select(Role).where(Role.name == "digital_ambassador"))
    role = role_result.scalar_one_or_none()
    if role:
        user.roles.append(role)

    db.add(user)
    await db.commit()
    await db.refresh(user, attribute_names=["roles"])
    return UserOut(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        roles=[r.name for r in user.roles],
        is_active=user.is_active,
    )


@router.get("/me", response_model=UserOut)
async def me(current_user: Annotated[User, Depends(get_current_user)]):
    return UserOut(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        roles=[r.name for r in current_user.roles],
        is_active=current_user.is_active,
    )
