"""
Deep intelligence endpoints – narratives, misinfo, auto-recommendations, geo density.
"""

from typing import Annotated, List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.listen import SocialPost, Alert
from app.models.ambassador import DigitalAmbassador
from app.models.geo import GeoHierarchy
from app.models.recommendation import Recommendation
from app.services.narrative import detect_narratives, suggest_response

router = APIRouter()


@router.get("/narratives")
async def analyze_narratives(
    db: Annotated[AsyncSession, Depends(get_db)],
    hours: int = Query(24, le=168),
    limit: int = Query(200, le=500),
):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    result = await db.execute(
        select(SocialPost.content)
        .where(SocialPost.ingested_at >= cutoff)
        .order_by(desc(SocialPost.ingested_at))
        .limit(limit)
    )
    texts = [r[0] for r in result.all() if r[0]]
    analysis = detect_narratives(texts)
    for n in analysis.get("narratives", []):
        n["suggested_response"] = suggest_response(n["type"])
    return analysis


@router.post("/generate-recommendations")
async def generate_recommendations(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    hours: int = 24,
):
    """
    Run narrative analysis and create pending Recommendation rows for human review.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    result = await db.execute(
        select(SocialPost.content)
        .where(SocialPost.ingested_at >= cutoff)
        .limit(200)
    )
    texts = [r[0] for r in result.all() if r[0]]
    analysis = detect_narratives(texts)
    created = []
    for n in analysis.get("narratives", []):
        if n.get("strength", 0) < 0.3:
            continue
        suggestion = suggest_response(n["type"])
        rec = Recommendation(
            title=n["label"],
            description=f"{suggestion['draft_hint']} Suggested spokesperson: {suggestion['spokesperson']}",
            action_type=suggestion["action"],
            confidence=round(n["strength"], 2),
            status="pending",
            ai_generated=True,
            metadata_={"narrative_type": n["type"], "misinfo_risk": analysis.get("misinfo_risk")},
        )
        db.add(rec)
        created.append(n["label"])
    await db.commit()
    return {
        "created": len(created),
        "titles": created,
        "misinfo_risk": analysis.get("misinfo_risk"),
        "message": "Recommendations queued for human review – not auto-executed",
    }


@router.get("/geo-density")
async def geo_density(db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Issue / coverage density by geo node for map heat layers.
    Uses ambassador coverage + post volume proxies.
    """
    # Ambassador coverage by ward
    amb_q = await db.execute(
        select(DigitalAmbassador.ward_id, func.count())
        .where(DigitalAmbassador.ward_id.isnot(None))
        .where(DigitalAmbassador.status.in_(["active", "verified"]))
        .group_by(DigitalAmbassador.ward_id)
    )
    amb_counts = {str(wid): cnt for wid, cnt in amb_q.all() if wid}

    # LGA list for map
    lgas = await db.execute(
        select(GeoHierarchy).where(GeoHierarchy.level == "lga").order_by(GeoHierarchy.name)
    )
    layers = []
    for g in lgas.scalars().all():
        # child wards coverage approximation
        layers.append({
            "geo_id": str(g.id),
            "name": g.name,
            "level": g.level,
            "ambassador_coverage": 0,  # filled if we had ward→lga rollup
            "is_placeholder": g.is_placeholder,
        })

    # Sentiment mix overall as state-level signal
    sent = await db.execute(
        select(SocialPost.sentiment, func.count()).group_by(SocialPost.sentiment)
    )
    sentiment_mix = {s or "unknown": c for s, c in sent.all()}

    return {
        "lga_layers": layers,
        "ward_ambassador_counts": amb_counts,
        "sentiment_mix": sentiment_mix,
        "note": "Polygon heat maps require official boundary geometries – points/centroids used until then",
    }


@router.get("/summary")
async def intelligence_summary(db: Annotated[AsyncSession, Depends(get_db)]):
    posts = await db.scalar(select(func.count()).select_from(SocialPost)) or 0
    open_alerts = await db.scalar(
        select(func.count()).select_from(Alert).where(Alert.status == "open")
    ) or 0
    pending_recs = await db.scalar(
        select(func.count()).select_from(Recommendation).where(Recommendation.status == "pending")
    ) or 0
    return {
        "posts_indexed": posts,
        "open_alerts": open_alerts,
        "pending_recommendations": pending_recs,
        "ai_method": "heuristic_v1 + rule sentiment/topics",
    }
