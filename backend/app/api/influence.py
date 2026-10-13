"""
Amplify & Influence – influencers, rapid response queue, counter-narratives.
All drafts require human approval before any distribution task is created.
"""

from typing import Annotated, List, Optional
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.influence import Influencer, RapidResponse
from app.models.task import Task, TaskAssignment
from app.models.ambassador import DigitalAmbassador
from app.services.intelligence import classify_sentiment

router = APIRouter()


class InfluencerCreate(BaseModel):
    handle: str
    platform: str
    display_name: Optional[str] = None
    category: str = "neutral"
    reach: int = 0
    engagement_rate: float = 0
    geo_id: Optional[UUID] = None
    notes: Optional[str] = None


class InfluencerOut(BaseModel):
    id: str
    handle: str
    platform: str
    display_name: Optional[str]
    category: str
    reach: int
    engagement_rate: float
    influence_score: float
    credibility: float


class RapidCreate(BaseModel):
    title: str
    narrative_type: str = "counter_narrative"
    draft_body: Optional[str] = None
    priority: str = "high"
    trigger_alert_id: Optional[UUID] = None
    geo_id: Optional[UUID] = None
    auto_draft: bool = True  # generate stub counter-narrative text


class RapidOut(BaseModel):
    id: str
    title: str
    narrative_type: str
    draft_body: Optional[str]
    status: str
    priority: str
    ai_generated: bool
    created_at: datetime


class RapidReview(BaseModel):
    action: str  # approve | reject
    notes: Optional[str] = None
    ambassador_ids: List[UUID] = []


def _score_influencer(reach: int, engagement_rate: float, credibility: float) -> float:
    # Simple composite 0-100
    reach_norm = min(reach / 100000, 1.0) * 40
    eng_norm = min(engagement_rate / 10, 1.0) * 40
    cred = credibility * 20
    return round(reach_norm + eng_norm + cred, 1)


@router.post("/influencers", response_model=InfluencerOut, status_code=201)
async def create_influencer(
    payload: InfluencerCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    score = _score_influencer(payload.reach, payload.engagement_rate, 0.5)
    inf = Influencer(
        handle=payload.handle,
        platform=payload.platform,
        display_name=payload.display_name or payload.handle,
        category=payload.category,
        reach=payload.reach,
        engagement_rate=payload.engagement_rate,
        influence_score=score,
        credibility=0.5,
        geo_id=payload.geo_id,
        notes=payload.notes,
    )
    db.add(inf)
    await db.commit()
    await db.refresh(inf)
    return _inf_out(inf)


@router.get("/influencers", response_model=List[InfluencerOut])
async def list_influencers(
    db: Annotated[AsyncSession, Depends(get_db)],
    category: Optional[str] = None,
    platform: Optional[str] = None,
    limit: int = Query(50, le=200),
):
    q = select(Influencer).order_by(desc(Influencer.influence_score)).limit(limit)
    if category:
        q = q.where(Influencer.category == category)
    if platform:
        q = q.where(Influencer.platform == platform)
    result = await db.execute(q)
    return [_inf_out(i) for i in result.scalars().all()]


@router.post("/rapid-response", response_model=RapidOut, status_code=201)
async def create_rapid_response(
    payload: RapidCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    body = payload.draft_body
    if payload.auto_draft and not body:
        # Stub AI counter-narrative – never published automatically
        body = (
            f"[DRAFT – FOR INTERNAL REVIEW ONLY]\n\n"
            f"Counter-narrative response to: {payload.title}\n\n"
            f"Key points to emphasize:\n"
            f"1. Acknowledge citizen concerns with empathy\n"
            f"2. Present verified facts and ongoing government actions\n"
            f"3. Invite constructive engagement\n"
            f"4. Direct to official channels for updates\n\n"
            f"Tone: calm, factual, hopeful. Requires human edit and approval before any distribution."
        )
    item = RapidResponse(
        title=payload.title,
        narrative_type=payload.narrative_type,
        draft_body=body,
        priority=payload.priority,
        trigger_alert_id=payload.trigger_alert_id,
        geo_id=payload.geo_id,
        ai_generated=payload.auto_draft,
        status="queued",
        assigned_to=current_user.id,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return _rapid_out(item)


@router.get("/rapid-response", response_model=List[RapidOut])
async def list_rapid(
    db: Annotated[AsyncSession, Depends(get_db)],
    status: Optional[str] = None,
    limit: int = Query(30, le=100),
):
    q = select(RapidResponse).order_by(desc(RapidResponse.created_at)).limit(limit)
    if status:
        q = q.where(RapidResponse.status == status)
    result = await db.execute(q)
    return [_rapid_out(r) for r in result.scalars().all()]


@router.post("/rapid-response/{item_id}/review")
async def review_rapid(
    item_id: UUID,
    payload: RapidReview,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    item = await db.get(RapidResponse, item_id)
    if not item:
        raise HTTPException(404, "Not found")
    if item.status not in ("queued", "in_review"):
        raise HTTPException(400, f"Already {item.status}")

    if payload.action == "reject":
        item.status = "rejected"
        item.approved_by = current_user.id
        item.approved_at = datetime.now(timezone.utc)
        await db.commit()
        return {"status": "rejected"}

    item.status = "approved"
    item.approved_by = current_user.id
    item.approved_at = datetime.now(timezone.utc)

    task_id = None
    assigned = 0
    if payload.ambassador_ids:
        task = Task(
            title=f"Rapid response: {item.title}",
            description=item.draft_body,
            task_type="rapid_response",
            priority=item.priority,
            created_by=current_user.id,
            geo_id=item.geo_id,
            status="open",
        )
        db.add(task)
        await db.flush()
        task_id = str(task.id)
        for amb_id in payload.ambassador_ids:
            amb = await db.get(DigitalAmbassador, amb_id)
            if not amb:
                continue
            db.add(TaskAssignment(task_id=task.id, ambassador_id=amb_id, status="assigned"))
            amb.total_tasks = (amb.total_tasks or 0) + 1
            assigned += 1
        item.status = "executed"

    await db.commit()
    return {
        "status": item.status,
        "task_id": task_id,
        "ambassadors_assigned": assigned,
        "message": "Approved for internal distribution only – no auto-publish",
    }


@router.post("/influencers/seed-demo")
async def seed_influencers(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    demos = [
        Influencer(handle="@lagosyouthvoice", platform="x", display_name="Lagos Youth Voice", category="youth", reach=45000, engagement_rate=4.2, influence_score=_score_influencer(45000, 4.2, 0.6), credibility=0.6),
        Influencer(handle="@ikejacommunity", platform="facebook", display_name="Ikeja Community", category="community", reach=22000, engagement_rate=3.1, influence_score=_score_influencer(22000, 3.1, 0.7), credibility=0.7),
        Influencer(handle="@ngrreporter", platform="x", display_name="NG Reporter", category="media", reach=180000, engagement_rate=2.5, influence_score=_score_influencer(180000, 2.5, 0.5), credibility=0.5),
        Influencer(handle="@faithlagos", platform="instagram", display_name="Faith Lagos", category="religious", reach=90000, engagement_rate=5.0, influence_score=_score_influencer(90000, 5.0, 0.8), credibility=0.8),
    ]
    for d in demos:
        db.add(d)
    await db.commit()
    return {"seeded": len(demos)}


def _inf_out(i: Influencer) -> InfluencerOut:
    return InfluencerOut(
        id=str(i.id),
        handle=i.handle,
        platform=i.platform,
        display_name=i.display_name,
        category=i.category,
        reach=i.reach,
        engagement_rate=i.engagement_rate,
        influence_score=i.influence_score,
        credibility=i.credibility,
    )


def _rapid_out(r: RapidResponse) -> RapidOut:
    return RapidOut(
        id=str(r.id),
        title=r.title,
        narrative_type=r.narrative_type,
        draft_body=r.draft_body,
        status=r.status,
        priority=r.priority,
        ai_generated=r.ai_generated,
        created_at=r.created_at,
    )
