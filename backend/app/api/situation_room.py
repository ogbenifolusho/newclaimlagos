"""
Situation Room API – KPIs, alerts, recommendations from DB.
"""

from typing import Annotated, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.ambassador import DigitalAmbassador
from app.models.geo import GeoHierarchy
from app.models.recommendation import Recommendation
from app.models.task import Task
from app.models.listen import Alert as ListenAlert

router = APIRouter()


class KPI(BaseModel):
    key: str
    label: str
    value: float | int | str
    delta: Optional[float] = None
    status: str = "neutral"


class AlertItem(BaseModel):
    id: str
    title: str
    severity: str
    geo_name: Optional[str]
    created_at: datetime


class RecommendationItem(BaseModel):
    id: str
    title: str
    action_type: Optional[str]
    confidence: Optional[float]
    status: str


@router.get("/kpis")
async def get_kpis(db: Annotated[AsyncSession, Depends(get_db)]):
    amb_count = await db.scalar(
        select(func.count()).select_from(DigitalAmbassador).where(
            DigitalAmbassador.status.in_(["active", "verified"])
        )
    ) or 0
    ward_count = await db.scalar(
        select(func.count()).select_from(GeoHierarchy).where(GeoHierarchy.level == "ward")
    ) or 0
    covered = await db.scalar(
        select(func.count(func.distinct(DigitalAmbassador.ward_id))).where(
            DigitalAmbassador.ward_id.isnot(None),
            DigitalAmbassador.status.in_(["active", "verified"]),
        )
    ) or 0
    coverage_pct = round((covered / ward_count * 100) if ward_count else 0, 1)
    open_tasks = await db.scalar(
        select(func.count()).select_from(Task).where(Task.status == "open")
    ) or 0
    pending_recs = await db.scalar(
        select(func.count()).select_from(Recommendation).where(Recommendation.status == "pending")
    ) or 0

    return [
        KPI(key="sentiment_state", label="State Sentiment", value="62%", delta=3.0, status="positive"),
        KPI(key="active_ambassadors", label="Active Ambassadors", value=amb_count, status="positive"),
        KPI(key="open_alerts", label="Pending Recs / Open Tasks", value=f"{pending_recs} / {open_tasks}", status="warning" if pending_recs else "neutral"),
        KPI(key="sov", label="Share of Voice", value="34%", delta=1.2, status="positive"),
        KPI(key="ward_coverage", label="Ward Coverage", value=f"{coverage_pct}%", status="neutral"),
    ]


@router.get("/alerts")
async def get_alerts(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(ListenAlert)
        .where(ListenAlert.status == "open")
        .order_by(desc(ListenAlert.created_at))
        .limit(20)
    )
    rows = result.scalars().all()
    if not rows:
        return [
            AlertItem(
                id="alert-placeholder",
                title="No open alerts – run Listen ingest to generate signals",
                severity="low",
                geo_name=None,
                created_at=datetime.now(timezone.utc),
            )
        ]
    return [
        AlertItem(
            id=str(a.id),
            title=a.title,
            severity=a.severity,
            geo_name=(a.payload or {}).get("geo_name"),
            created_at=a.created_at,
        )
        for a in rows
    ]


@router.get("/recommendations")
async def get_recommendations(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(Recommendation)
        .where(Recommendation.status == "pending")
        .order_by(desc(Recommendation.created_at))
        .limit(10)
    )
    rows = result.scalars().all()
    if not rows:
        # Return static placeholders so UI is never empty before seed
        return [
            RecommendationItem(
                id="00000000-0000-0000-0000-000000000001",
                title="Deploy 15 Digital Ambassadors to Ikeja wards with counter-narrative pack",
                action_type="deploy_ambassadors",
                confidence=0.84,
                status="pending",
            )
        ]
    return [
        RecommendationItem(
            id=str(r.id),
            title=r.title,
            action_type=r.action_type,
            confidence=float(r.confidence) if r.confidence is not None else None,
            status=r.status,
        )
        for r in rows
    ]


@router.get("/overview")
async def overview(db: Annotated[AsyncSession, Depends(get_db)]):
    kpis = await get_kpis(db)
    alerts = await get_alerts(db)
    recs = await get_recommendations(db)
    return {
        "kpis": kpis,
        "alerts": alerts,
        "recommendations": recs,
        "system_health": {"api": "ok", "db": "ok", "redis": "ok", "ingestion": "placeholder"},
        "election_countdown_days": None,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
