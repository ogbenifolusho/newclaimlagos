"""
Digital Ambassador Management – list, create, verify, leaderboard.
"""

from typing import Annotated, List, Optional
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.user import User, Role
from app.models.ambassador import DigitalAmbassador
from app.models.geo import GeoHierarchy

router = APIRouter()


class AmbassadorOut(BaseModel):
    id: str
    user_id: str
    full_name: str
    email: str
    ward_id: Optional[str]
    ward_name: Optional[str]
    status: str
    performance_score: float
    completed_tasks: int
    total_tasks: int
    phone: Optional[str] = None

    class Config:
        from_attributes = True


class AmbassadorCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    ward_id: Optional[UUID] = None


class AmbassadorVerify(BaseModel):
    status: str  # verified | active | suspended
    notes: Optional[str] = None


@router.get("/", response_model=List[AmbassadorOut])
async def list_ambassadors(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    status_filter: Optional[str] = Query(None, alias="status"),
    ward_id: Optional[UUID] = None,
    limit: int = Query(50, le=200),
):
    q = (
        select(DigitalAmbassador, User, GeoHierarchy)
        .join(User, DigitalAmbassador.user_id == User.id)
        .outerjoin(GeoHierarchy, DigitalAmbassador.ward_id == GeoHierarchy.id)
    )
    if status_filter:
        q = q.where(DigitalAmbassador.status == status_filter)
    if ward_id:
        q = q.where(DigitalAmbassador.ward_id == ward_id)
    q = q.order_by(desc(DigitalAmbassador.performance_score)).limit(limit)
    result = await db.execute(q)
    rows = result.all()
    return [
        AmbassadorOut(
            id=str(amb.id),
            user_id=str(amb.user_id),
            full_name=user.full_name,
            email=user.email,
            ward_id=str(amb.ward_id) if amb.ward_id else None,
            ward_name=geo.name if geo else None,
            status=amb.status,
            performance_score=float(amb.performance_score or 0),
            completed_tasks=amb.completed_tasks or 0,
            total_tasks=amb.total_tasks or 0,
            phone=amb.phone,
        )
        for amb, user, geo in rows
    ]


@router.post("/", response_model=AmbassadorOut, status_code=201)
async def create_ambassador(
    payload: AmbassadorCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        phone=payload.phone,
        hashed_password=get_password_hash(payload.password),
        is_active=True,
    )
    role_res = await db.execute(select(Role).where(Role.name == "digital_ambassador"))
    role = role_res.scalar_one_or_none()
    if role:
        user.roles.append(role)
    db.add(user)
    await db.flush()

    amb = DigitalAmbassador(
        user_id=user.id,
        ward_id=payload.ward_id,
        phone=payload.phone,
        whatsapp=payload.whatsapp,
        status="pending",
    )
    db.add(amb)
    await db.commit()
    await db.refresh(amb)

    ward_name = None
    if amb.ward_id:
        g = await db.get(GeoHierarchy, amb.ward_id)
        ward_name = g.name if g else None

    return AmbassadorOut(
        id=str(amb.id),
        user_id=str(user.id),
        full_name=user.full_name,
        email=user.email,
        ward_id=str(amb.ward_id) if amb.ward_id else None,
        ward_name=ward_name,
        status=amb.status,
        performance_score=0,
        completed_tasks=0,
        total_tasks=0,
        phone=amb.phone,
    )


@router.patch("/{ambassador_id}/verify", response_model=AmbassadorOut)
async def verify_ambassador(
    ambassador_id: UUID,
    payload: AmbassadorVerify,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    amb = await db.get(DigitalAmbassador, ambassador_id)
    if not amb:
        raise HTTPException(status_code=404, detail="Ambassador not found")
    amb.status = payload.status
    amb.verification_notes = payload.notes
    amb.verified_at = datetime.now(timezone.utc)
    amb.verified_by = current_user.id
    await db.commit()

    user = await db.get(User, amb.user_id)
    ward_name = None
    if amb.ward_id:
        g = await db.get(GeoHierarchy, amb.ward_id)
        ward_name = g.name if g else None

    return AmbassadorOut(
        id=str(amb.id),
        user_id=str(amb.user_id),
        full_name=user.full_name if user else "",
        email=user.email if user else "",
        ward_id=str(amb.ward_id) if amb.ward_id else None,
        ward_name=ward_name,
        status=amb.status,
        performance_score=float(amb.performance_score or 0),
        completed_tasks=amb.completed_tasks or 0,
        total_tasks=amb.total_tasks or 0,
        phone=amb.phone,
    )


@router.get("/leaderboard")
async def leaderboard(
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 20,
):
    q = (
        select(DigitalAmbassador, User)
        .join(User, DigitalAmbassador.user_id == User.id)
        .where(DigitalAmbassador.status.in_(["active", "verified"]))
        .order_by(desc(DigitalAmbassador.performance_score))
        .limit(limit)
    )
    result = await db.execute(q)
    rows = result.all()
    return {
        "period": "all_time",
        "leaders": [
            {
                "rank": i + 1,
                "name": user.full_name,
                "score": float(amb.performance_score or 0),
                "tasks_completed": amb.completed_tasks or 0,
            }
            for i, (amb, user) in enumerate(rows)
        ],
    }
