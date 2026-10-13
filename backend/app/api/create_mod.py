"""
CREATE module – calendar events + AI-assisted draft generation (approval only).
"""

from typing import Annotated, List, Optional
from uuid import UUID
from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.calendar import CalendarEvent
from app.models.content import ContentAsset

router = APIRouter()


class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    event_date: date
    event_type: str = "other"
    geo_id: Optional[UUID] = None


class EventOut(BaseModel):
    id: str
    title: str
    description: Optional[str]
    event_date: date
    event_type: str


class AIDraftRequest(BaseModel):
    topic: str
    tone: str = "hopeful"  # hopeful|factual|empathetic
    platform: str = "x"
    geo_hint: Optional[str] = None


@router.post("/calendar", response_model=EventOut, status_code=201)
async def create_event(
    payload: EventCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    ev = CalendarEvent(
        title=payload.title,
        description=payload.description,
        event_date=payload.event_date,
        event_type=payload.event_type,
        geo_id=payload.geo_id,
        created_by=current_user.id,
    )
    db.add(ev)
    await db.commit()
    await db.refresh(ev)
    return EventOut(
        id=str(ev.id),
        title=ev.title,
        description=ev.description,
        event_date=ev.event_date,
        event_type=ev.event_type,
    )


@router.get("/calendar", response_model=List[EventOut])
async def list_events(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(CalendarEvent).order_by(CalendarEvent.event_date).limit(100)
    )
    return [
        EventOut(
            id=str(e.id),
            title=e.title,
            description=e.description,
            event_date=e.event_date,
            event_type=e.event_type,
        )
        for e in result.scalars().all()
    ]


@router.post("/ai-draft")
async def generate_ai_draft(
    payload: AIDraftRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Generate a content draft for internal review only.
    Saved as content_assets with status=pending_review, ai_generated=True.
    Never published automatically.
    """
    tone_map = {
        "hopeful": "optimistic and forward-looking",
        "factual": "precise and evidence-based",
        "empathetic": "understanding and citizen-centred",
    }
    tone_desc = tone_map.get(payload.tone, "balanced")
    geo = f" in {payload.geo_hint}" if payload.geo_hint else " across Lagos"
    draft = (
        f"[AI DRAFT – REQUIRES HUMAN APPROVAL]\n\n"
        f"Platform: {payload.platform}\n"
        f"Topic: {payload.topic}\n\n"
        f"Suggested copy ({tone_desc}):\n\n"
        f"Lagosians{geo} deserve clear progress on {payload.topic}. "
        f"We are listening, delivering, and accountable. "
        f"Share your experience – together we build the Lagos we want.\n\n"
        f"#LagosProgress #PBATKOH2027\n\n"
        f"---\nEdit freely. Approve in Content module before any distribution task."
    )
    asset = ContentAsset(
        title=f"AI Draft: {payload.topic[:80]}",
        body=draft,
        asset_type=payload.platform,
        status="pending_review",
        created_by=current_user.id,
        ai_generated=True,
        ai_prompt=f"topic={payload.topic}; tone={payload.tone}; platform={payload.platform}",
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return {
        "content_id": str(asset.id),
        "status": "pending_review",
        "draft_preview": draft[:400],
        "message": "Draft saved for human review – not published",
    }
