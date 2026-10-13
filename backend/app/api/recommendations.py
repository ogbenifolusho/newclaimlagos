"""
Recommendations – list, review, convert to tasks (human-in-the-loop).
"""

from typing import Annotated, List, Optional
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.recommendation import Recommendation
from app.models.task import Task, TaskAssignment
from app.models.ambassador import DigitalAmbassador

router = APIRouter()


class RecommendationOut(BaseModel):
    id: str
    title: str
    description: Optional[str]
    action_type: Optional[str]
    confidence: Optional[float]
    status: str
    geo_id: Optional[str]
    created_at: datetime


class ReviewRequest(BaseModel):
    action: str  # accept | reject
    notes: Optional[str] = None
    # When accepting a deploy_ambassadors action:
    ambassador_ids: List[UUID] = []
    task_title: Optional[str] = None
    task_description: Optional[str] = None


@router.get("/", response_model=List[RecommendationOut])
async def list_recommendations(
    db: Annotated[AsyncSession, Depends(get_db)],
    status: Optional[str] = "pending",
    limit: int = 20,
):
    q = select(Recommendation).order_by(desc(Recommendation.created_at)).limit(limit)
    if status:
        q = q.where(Recommendation.status == status)
    result = await db.execute(q)
    rows = result.scalars().all()
    return [
        RecommendationOut(
            id=str(r.id),
            title=r.title,
            description=r.description,
            action_type=r.action_type,
            confidence=float(r.confidence) if r.confidence is not None else None,
            status=r.status,
            geo_id=str(r.geo_id) if r.geo_id else None,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/{rec_id}/review")
async def review_recommendation(
    rec_id: UUID,
    payload: ReviewRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Human reviews an AI recommendation.
    - reject → mark rejected
    - accept → mark accepted and optionally create tasks + assignments
    Never auto-publishes anything.
    """
    rec = await db.get(Recommendation, rec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if rec.status != "pending":
        raise HTTPException(status_code=400, detail=f"Already {rec.status}")

    if payload.action == "reject":
        rec.status = "rejected"
        rec.reviewed_by = current_user.id
        rec.reviewed_at = datetime.now(timezone.utc)
        await db.commit()
        return {"status": "rejected", "recommendation_id": str(rec.id)}

    if payload.action != "accept":
        raise HTTPException(status_code=400, detail="action must be accept or reject")

    rec.status = "accepted"
    rec.reviewed_by = current_user.id
    rec.reviewed_at = datetime.now(timezone.utc)

    created_task_id = None
    assigned = 0

    if payload.ambassador_ids or payload.task_title:
        task = Task(
            title=payload.task_title or rec.title,
            description=payload.task_description or rec.description,
            task_type=rec.action_type or "follow_up",
            priority="high",
            geo_id=rec.geo_id,
            created_by=current_user.id,
            source_recommendation_id=rec.id,
            status="open",
        )
        db.add(task)
        await db.flush()
        created_task_id = str(task.id)

        for amb_id in payload.ambassador_ids:
            amb = await db.get(DigitalAmbassador, amb_id)
            if not amb:
                continue
            db.add(TaskAssignment(task_id=task.id, ambassador_id=amb_id, status="assigned"))
            amb.total_tasks = (amb.total_tasks or 0) + 1
            assigned += 1

    await db.commit()
    return {
        "status": "accepted",
        "recommendation_id": str(rec.id),
        "task_id": created_task_id,
        "ambassadors_assigned": assigned,
        "message": "Recommendation accepted. Task created for human execution only – no auto-publish.",
    }


@router.post("/seed-demo")
async def seed_demo_recommendations(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Seed a couple of demo recommendations for Situation Room testing."""
    demos = [
        Recommendation(
            title="Deploy 15 Digital Ambassadors to Ikeja wards with counter-narrative pack",
            description="Negative transport narrative rising. Assign verified ambassadors with approved content pack.",
            action_type="deploy_ambassadors",
            confidence=0.84,
            status="pending",
            ai_generated=True,
        ),
        Recommendation(
            title="Increase organic amplification on transport achievements content",
            description="Share of voice opportunity on road projects. Schedule approved creatives for ambassador distribution.",
            action_type="amplify_content",
            confidence=0.76,
            status="pending",
            ai_generated=True,
        ),
    ]
    for d in demos:
        db.add(d)
    await db.commit()
    return {"seeded": len(demos)}
