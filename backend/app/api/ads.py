"""
Digital Advertising – campaign lifecycle placeholders (Meta, Google, X, TikTok, YouTube).
No live ad spend without real credentials; synthetic metrics for testing.
"""

from typing import Annotated, List, Optional
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
import random

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.ads import AdCampaign, AdCreative

router = APIRouter()

PLATFORMS = ["meta", "google", "x", "tiktok", "youtube"]


class CampaignCreate(BaseModel):
    name: str
    platform: str
    budget: Optional[float] = None
    objective: Optional[str] = "awareness"
    status: str = "draft"


class CampaignOut(BaseModel):
    id: str
    name: str
    platform: str
    status: str
    budget: Optional[float]
    spend: float
    metrics: dict
    objective: Optional[str]
    created_at: datetime


class CreativeCreate(BaseModel):
    name: str
    body: Optional[str] = None
    media_urls: List[str] = []


@router.post("/campaigns", response_model=CampaignOut, status_code=201)
async def create_campaign(
    payload: CampaignCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    if payload.platform not in PLATFORMS:
        raise HTTPException(400, f"platform must be one of {PLATFORMS}")
    camp = AdCampaign(
        name=payload.name,
        platform=payload.platform,
        budget=payload.budget,
        objective=payload.objective,
        status=payload.status,
        created_by=current_user.id,
        metrics={},
    )
    db.add(camp)
    await db.commit()
    await db.refresh(camp)
    return _camp_out(camp)


@router.get("/campaigns", response_model=List[CampaignOut])
async def list_campaigns(
    db: Annotated[AsyncSession, Depends(get_db)],
    platform: Optional[str] = None,
    status: Optional[str] = None,
):
    q = select(AdCampaign).order_by(desc(AdCampaign.created_at))
    if platform:
        q = q.where(AdCampaign.platform == platform)
    if status:
        q = q.where(AdCampaign.status == status)
    result = await db.execute(q)
    return [_camp_out(c) for c in result.scalars().all()]


@router.post("/campaigns/{campaign_id}/creatives", status_code=201)
async def add_creative(
    campaign_id: UUID,
    payload: CreativeCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    camp = await db.get(AdCampaign, campaign_id)
    if not camp:
        raise HTTPException(404, "Campaign not found")
    creative = AdCreative(
        campaign_id=campaign_id,
        name=payload.name,
        body=payload.body,
        media_urls=payload.media_urls,
        status="pending_review",
    )
    db.add(creative)
    await db.commit()
    return {"id": str(creative.id), "status": creative.status, "note": "Creative pending human review – not published"}


@router.post("/campaigns/{campaign_id}/sync-metrics")
async def sync_metrics(
    campaign_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Placeholder metric sync – synthetic when no live Ads API credentials."""
    camp = await db.get(AdCampaign, campaign_id)
    if not camp:
        raise HTTPException(404, "Campaign not found")
    # Synthetic performance for demo
    impressions = random.randint(5000, 80000)
    clicks = int(impressions * random.uniform(0.01, 0.05))
    spend = round(float(camp.budget or 1000) * random.uniform(0.1, 0.6), 2)
    camp.spend = spend
    camp.metrics = {
        "impressions": impressions,
        "reach": int(impressions * 0.7),
        "clicks": clicks,
        "ctr": round(clicks / impressions * 100, 2),
        "cpc": round(spend / max(clicks, 1), 2),
        "cpm": round(spend / impressions * 1000, 2),
        "source": "synthetic_placeholder",
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }
    camp.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"campaign_id": str(camp.id), "metrics": camp.metrics, "spend": float(camp.spend)}


@router.get("/summary")
async def ads_summary(db: Annotated[AsyncSession, Depends(get_db)]):
    total = await db.scalar(select(func.count()).select_from(AdCampaign)) or 0
    active = await db.scalar(
        select(func.count()).select_from(AdCampaign).where(AdCampaign.status == "active")
    ) or 0
    spend = await db.scalar(select(func.coalesce(func.sum(AdCampaign.spend), 0))) or 0
    by_platform = await db.execute(
        select(AdCampaign.platform, func.count()).group_by(AdCampaign.platform)
    )
    return {
        "total_campaigns": total,
        "active": active,
        "total_spend": float(spend),
        "by_platform": {p: c for p, c in by_platform.all()},
        "note": "Live Ads APIs pending credentials – metrics may be synthetic",
    }


@router.post("/seed-demo")
async def seed_demo_ads(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    demos = [
        AdCampaign(name="Lagos Transport Story – Meta", platform="meta", budget=500000, status="active", objective="awareness", created_by=current_user.id, spend=120000, metrics={"impressions": 45000, "ctr": 2.1}),
        AdCampaign(name="Youth Jobs Narrative – TikTok", platform="tiktok", budget=300000, status="active", objective="engagement", created_by=current_user.id, spend=80000, metrics={"impressions": 120000, "ctr": 3.4}),
        AdCampaign(name="Search – Governance Keywords", platform="google", budget=200000, status="paused", objective="traffic", created_by=current_user.id, spend=45000, metrics={"impressions": 12000, "ctr": 4.0}),
    ]
    for d in demos:
        db.add(d)
    await db.commit()
    return {"seeded": len(demos)}


def _camp_out(c: AdCampaign) -> CampaignOut:
    return CampaignOut(
        id=str(c.id),
        name=c.name,
        platform=c.platform,
        status=c.status,
        budget=float(c.budget) if c.budget is not None else None,
        spend=float(c.spend or 0),
        metrics=c.metrics or {},
        objective=c.objective,
        created_at=c.created_at,
    )
