"""
Reporting suite – JSON/CSV exports and executive summaries.
PDF/PPT can be added later with reportlab/python-pptx when deps allow.
"""

from typing import Annotated, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
import csv
import io
import json

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.ambassador import DigitalAmbassador
from app.models.listen import SocialPost, Alert
from app.models.ads import AdCampaign
from app.models.task import Task
from app.models.recommendation import Recommendation
from app.models.geo import GeoHierarchy
from app.services.narrative import detect_narratives

router = APIRouter()


@router.get("/executive")
async def executive_report(db: Annotated[AsyncSession, Depends(get_db)]):
    """One-shot executive summary for Situation Room / leadership."""
    amb_active = await db.scalar(
        select(func.count()).select_from(DigitalAmbassador).where(
            DigitalAmbassador.status.in_(["active", "verified"])
        )
    ) or 0
    posts = await db.scalar(select(func.count()).select_from(SocialPost)) or 0
    open_alerts = await db.scalar(
        select(func.count()).select_from(Alert).where(Alert.status == "open")
    ) or 0
    open_tasks = await db.scalar(
        select(func.count()).select_from(Task).where(Task.status == "open")
    ) or 0
    pending_recs = await db.scalar(
        select(func.count()).select_from(Recommendation).where(Recommendation.status == "pending")
    ) or 0
    ad_spend = await db.scalar(select(func.coalesce(func.sum(AdCampaign.spend), 0))) or 0
    wards = await db.scalar(
        select(func.count()).select_from(GeoHierarchy).where(GeoHierarchy.level == "ward")
    ) or 0
    covered = await db.scalar(
        select(func.count(func.distinct(DigitalAmbassador.ward_id))).where(
            DigitalAmbassador.ward_id.isnot(None),
            DigitalAmbassador.status.in_(["active", "verified"]),
        )
    ) or 0

    # Narrative snapshot
    result = await db.execute(select(SocialPost.content).order_by(desc(SocialPost.ingested_at)).limit(100))
    texts = [r[0] for r in result.all() if r[0]]
    narratives = detect_narratives(texts)

    sent = await db.execute(select(SocialPost.sentiment, func.count()).group_by(SocialPost.sentiment))
    sentiment = {s or "unknown": c for s, c in sent.all()}

    ai_summary = (
        f"CLAIM LAGOS executive snapshot: {amb_active} active ambassadors covering "
        f"{covered}/{wards} wards. {posts} social posts indexed, {open_alerts} open alerts, "
        f"{pending_recs} recommendations awaiting human review, {open_tasks} open tasks. "
        f"Ad spend tracked: ₦{float(ad_spend):,.0f}. "
        f"Narrative risk: {narratives.get('misinfo_risk', 'unknown')} "
        f"(method={narratives.get('method')})."
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "kpis": {
            "active_ambassadors": amb_active,
            "ward_coverage": f"{covered}/{wards}",
            "posts_indexed": posts,
            "open_alerts": open_alerts,
            "pending_recommendations": pending_recs,
            "open_tasks": open_tasks,
            "ad_spend": float(ad_spend),
            "sentiment": sentiment,
        },
        "narratives": narratives,
        "ai_summary": ai_summary,
        "note": "All recommendations remain human-gated",
    }


@router.get("/export/ambassadors.csv")
async def export_ambassadors_csv(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    from app.models.user import User as UserModel
    q = (
        select(DigitalAmbassador, UserModel)
        .join(UserModel, DigitalAmbassador.user_id == UserModel.id)
        .order_by(desc(DigitalAmbassador.performance_score))
    )
    result = await db.execute(q)
    rows = result.all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "full_name", "email", "status", "performance_score", "completed_tasks", "total_tasks", "ward_id"])
    for amb, user in rows:
        writer.writerow([
            str(amb.id), user.full_name, user.email, amb.status,
            float(amb.performance_score or 0), amb.completed_tasks, amb.total_tasks,
            str(amb.ward_id) if amb.ward_id else "",
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ambassadors.csv"},
    )


@router.get("/export/posts.csv")
async def export_posts_csv(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(1000, le=5000),
):
    result = await db.execute(
        select(SocialPost).order_by(desc(SocialPost.ingested_at)).limit(limit)
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "platform", "author", "sentiment", "topics", "content", "ingested_at"])
    for p in result.scalars().all():
        writer.writerow([
            str(p.id), p.platform, p.author_handle, p.sentiment,
            ",".join(p.topics or []), (p.content or "")[:500],
            p.ingested_at.isoformat() if p.ingested_at else "",
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=social_posts.csv"},
    )


@router.get("/export/executive.json")
async def export_executive_json(db: Annotated[AsyncSession, Depends(get_db)]):
    data = await executive_report(db)
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": "attachment; filename=executive_report.json"},
    )
