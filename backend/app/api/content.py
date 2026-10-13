"""
Content packs – create drafts, approve, distribute to ambassadors (never auto-publish).
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
from app.models.content import ContentAsset, ContentApproval
from app.models.task import Task, TaskAssignment
from app.models.ambassador import DigitalAmbassador

router = APIRouter()


class ContentCreate(BaseModel):
    title: str
    body: Optional[str] = None
    asset_type: str = "post"
    ai_generated: bool = False
    ai_prompt: Optional[str] = None
    media_urls: List[str] = []
    target_geo_ids: List[UUID] = []


class ContentOut(BaseModel):
    id: str
    title: str
    body: Optional[str]
    asset_type: Optional[str]
    status: str
    ai_generated: bool
    created_at: datetime


class ApproveRequest(BaseModel):
    action: str  # approve | reject | request_changes
    comments: Optional[str] = None


class DistributeRequest(BaseModel):
    ambassador_ids: List[UUID]
    task_title: Optional[str] = None


@router.post("/", response_model=ContentOut, status_code=201)
async def create_content(
    payload: ContentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    asset = ContentAsset(
        title=payload.title,
        body=payload.body,
        asset_type=payload.asset_type,
        status="pending_review" if payload.ai_generated else "draft",
        created_by=current_user.id,
        ai_generated=payload.ai_generated,
        ai_prompt=payload.ai_prompt,
        media_urls=payload.media_urls,
        target_geo_ids=payload.target_geo_ids or None,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return ContentOut(
        id=str(asset.id),
        title=asset.title,
        body=asset.body,
        asset_type=asset.asset_type,
        status=asset.status,
        ai_generated=asset.ai_generated,
        created_at=asset.created_at,
    )


@router.get("/", response_model=List[ContentOut])
async def list_content(
    db: Annotated[AsyncSession, Depends(get_db)],
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
):
    q = select(ContentAsset).order_by(desc(ContentAsset.created_at)).limit(limit)
    if status:
        q = q.where(ContentAsset.status == status)
    result = await db.execute(q)
    return [
        ContentOut(
            id=str(c.id),
            title=c.title,
            body=c.body,
            asset_type=c.asset_type,
            status=c.status,
            ai_generated=c.ai_generated,
            created_at=c.created_at,
        )
        for c in result.scalars().all()
    ]


@router.post("/{content_id}/approve")
async def approve_content(
    content_id: UUID,
    payload: ApproveRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    asset = await db.get(ContentAsset, content_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Content not found")

    db.add(ContentApproval(
        content_id=asset.id,
        reviewer_id=current_user.id,
        action=payload.action,
        comments=payload.comments,
    ))

    if payload.action == "approve":
        asset.status = "approved"
        asset.approved_by = current_user.id
        asset.approved_at = datetime.now(timezone.utc)
    elif payload.action == "reject":
        asset.status = "rejected"
    else:
        asset.status = "draft"

    await db.commit()
    return {"status": asset.status, "content_id": str(asset.id)}


@router.post("/{content_id}/distribute")
async def distribute_content(
    content_id: UUID,
    payload: DistributeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Distribute approved content as tasks to ambassadors. Never publishes publicly."""
    asset = await db.get(ContentAsset, content_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Content not found")
    if asset.status != "approved":
        raise HTTPException(status_code=400, detail="Only approved content can be distributed")

    task = Task(
        title=payload.task_title or f"Distribute: {asset.title}",
        description=asset.body,
        task_type="content_distribution",
        priority="medium",
        created_by=current_user.id,
        content_asset_id=asset.id,
        status="open",
    )
    db.add(task)
    await db.flush()

    assigned = 0
    for amb_id in payload.ambassador_ids:
        amb = await db.get(DigitalAmbassador, amb_id)
        if not amb:
            continue
        db.add(TaskAssignment(task_id=task.id, ambassador_id=amb_id, status="assigned"))
        amb.total_tasks = (amb.total_tasks or 0) + 1
        assigned += 1

    await db.commit()
    return {
        "task_id": str(task.id),
        "ambassadors_assigned": assigned,
        "message": "Content distributed as internal tasks only – no public publishing",
    }
