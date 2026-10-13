"""
Listen module – keyword rules, ingest, search posts, trigger alerts.
"""

from typing import Annotated, List, Optional
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.listen import KeywordRule, SocialPost, Alert
from app.services.ingestion import fetch_platform_posts, process_post, PLATFORMS, platform_configured
from app.api.ws import publish_alert

router = APIRouter()


class KeywordRuleCreate(BaseModel):
    name: str
    keywords: List[str]
    platforms: List[str] = ["x", "facebook", "instagram", "youtube", "tiktok"]
    severity: str = "medium"
    geo_id: Optional[UUID] = None


class KeywordRuleOut(BaseModel):
    id: str
    name: str
    keywords: List[str]
    platforms: List[str]
    severity: str
    is_active: bool


class PostOut(BaseModel):
    id: str
    platform: str
    author_handle: Optional[str]
    content: Optional[str]
    sentiment: Optional[str]
    topics: Optional[List[str]]
    matched_keywords: Optional[List[str]]
    is_bot_suspect: bool
    ingested_at: datetime


class AlertOut(BaseModel):
    id: str
    title: str
    severity: str
    source: Optional[str]
    status: str
    created_at: datetime
    payload: dict = {}


# --- Keyword rules ---

@router.post("/keywords", response_model=KeywordRuleOut, status_code=201)
async def create_keyword_rule(
    payload: KeywordRuleCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    rule = KeywordRule(
        name=payload.name,
        keywords=payload.keywords,
        platforms=payload.platforms,
        severity=payload.severity,
        geo_id=payload.geo_id,
        created_by=current_user.id,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return KeywordRuleOut(
        id=str(rule.id),
        name=rule.name,
        keywords=rule.keywords or [],
        platforms=rule.platforms or [],
        severity=rule.severity,
        is_active=rule.is_active,
    )


@router.get("/keywords", response_model=List[KeywordRuleOut])
async def list_keyword_rules(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(KeywordRule).order_by(desc(KeywordRule.created_at)))
    return [
        KeywordRuleOut(
            id=str(r.id),
            name=r.name,
            keywords=r.keywords or [],
            platforms=r.platforms or [],
            severity=r.severity,
            is_active=r.is_active,
        )
        for r in result.scalars().all()
    ]


# --- Ingest ---

@router.post("/ingest")
async def run_ingest(
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    platform: Optional[str] = None,
    limit: int = Query(15, le=50),
):
    """
    Run ingestion for configured (or synthetic) platforms.
    Matches against active keyword rules and raises alerts.
    """
    rules_res = await db.execute(select(KeywordRule).where(KeywordRule.is_active == True))
    rules = rules_res.scalars().all()
    all_keywords = []
    for r in rules:
        all_keywords.extend(r.keywords or [])
    all_keywords = list(set(all_keywords)) or ["lagos", "transport", "governance"]

    platforms = [platform] if platform else PLATFORMS
    ingested = 0
    alerts_created = 0

    for plat in platforms:
        raw_posts = await fetch_platform_posts(plat, all_keywords, limit=limit)
        for raw in raw_posts:
            processed = await process_post(raw, all_keywords)
            post = SocialPost(
                platform=processed["platform"],
                external_id=processed.get("external_id"),
                author_handle=processed.get("author_handle"),
                content=processed.get("content"),
                sentiment=processed.get("sentiment"),
                sentiment_score=processed.get("sentiment_score"),
                topics=processed.get("topics"),
                language=processed.get("language"),
                engagement=processed.get("engagement") or {},
                is_bot_suspect=processed.get("is_bot_suspect", False),
                matched_keywords=processed.get("matched_keywords"),
                raw_payload=processed.get("raw_payload"),
                created_at=processed.get("created_at"),
            )
            db.add(post)
            ingested += 1

            # Alert if matched keywords and negative/mixed sentiment
            matched = processed.get("matched_keywords") or []
            if matched and processed.get("sentiment") in ("negative", "mixed"):
                title = f"[{plat}] Keyword match: {', '.join(matched[:3])} – {processed.get('sentiment')}"
                alert = Alert(
                    title=title[:255],
                    severity="high" if processed.get("sentiment") == "negative" else "medium",
                    source=plat,
                    payload={
                        "content": (processed.get("content") or "")[:300],
                        "author": processed.get("author_handle"),
                        "keywords": matched,
                        "topics": processed.get("topics"),
                    },
                    status="open",
                )
                db.add(alert)
                alerts_created += 1
                # Push to Situation Room WS
                background_tasks.add_task(
                    publish_alert,
                    title[:200],
                    alert.severity,
                    None,
                )

    await db.commit()
    return {
        "ingested": ingested,
        "alerts_created": alerts_created,
        "platforms": platforms,
        "credentials_configured": {p: platform_configured(p) for p in PLATFORMS},
        "note": "Synthetic data used where API credentials are empty placeholders",
    }


@router.get("/posts", response_model=List[PostOut])
async def list_posts(
    db: Annotated[AsyncSession, Depends(get_db)],
    platform: Optional[str] = None,
    sentiment: Optional[str] = None,
    limit: int = Query(50, le=200),
):
    q = select(SocialPost).order_by(desc(SocialPost.ingested_at)).limit(limit)
    if platform:
        q = q.where(SocialPost.platform == platform)
    if sentiment:
        q = q.where(SocialPost.sentiment == sentiment)
    result = await db.execute(q)
    return [
        PostOut(
            id=str(p.id),
            platform=p.platform,
            author_handle=p.author_handle,
            content=p.content,
            sentiment=p.sentiment,
            topics=p.topics,
            matched_keywords=p.matched_keywords,
            is_bot_suspect=p.is_bot_suspect or False,
            ingested_at=p.ingested_at,
        )
        for p in result.scalars().all()
    ]


@router.get("/alerts", response_model=List[AlertOut])
async def list_alerts(
    db: Annotated[AsyncSession, Depends(get_db)],
    status: Optional[str] = "open",
    limit: int = Query(30, le=100),
):
    q = select(Alert).order_by(desc(Alert.created_at)).limit(limit)
    if status:
        q = q.where(Alert.status == status)
    result = await db.execute(q)
    return [
        AlertOut(
            id=str(a.id),
            title=a.title,
            severity=a.severity,
            source=a.source,
            status=a.status,
            created_at=a.created_at,
            payload=a.payload or {},
        )
        for a in result.scalars().all()
    ]


@router.post("/alerts/{alert_id}/ack")
async def acknowledge_alert(
    alert_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = "acknowledged"
    alert.acknowledged_by = current_user.id
    alert.acknowledged_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "acknowledged", "id": str(alert.id)}


@router.get("/stats")
async def listen_stats(db: Annotated[AsyncSession, Depends(get_db)]):
    total = await db.scalar(select(func.count()).select_from(SocialPost)) or 0
    by_sentiment = await db.execute(
        select(SocialPost.sentiment, func.count()).group_by(SocialPost.sentiment)
    )
    by_platform = await db.execute(
        select(SocialPost.platform, func.count()).group_by(SocialPost.platform)
    )
    open_alerts = await db.scalar(
        select(func.count()).select_from(Alert).where(Alert.status == "open")
    ) or 0
    return {
        "total_posts": total,
        "by_sentiment": {s or "unknown": c for s, c in by_sentiment.all()},
        "by_platform": {p: c for p, c in by_platform.all()},
        "open_alerts": open_alerts,
        "credentials": {p: platform_configured(p) for p in PLATFORMS},
    }


@router.post("/keywords/seed-demo")
async def seed_demo_keywords(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    demos = [
        KeywordRule(
            name="Transport & Roads",
            keywords=["transport", "road", "roads", "traffic", "brt", "pothole"],
            platforms=PLATFORMS,
            severity="high",
            created_by=current_user.id,
        ),
        KeywordRule(
            name="Governance & Accountability",
            keywords=["governance", "corruption", "accountability", "leadership"],
            platforms=PLATFORMS,
            severity="high",
            created_by=current_user.id,
        ),
        KeywordRule(
            name="Economy & Jobs",
            keywords=["jobs", "unemployment", "economy", "naira", "inflation"],
            platforms=PLATFORMS,
            severity="medium",
            created_by=current_user.id,
        ),
    ]
    for d in demos:
        db.add(d)
    await db.commit()
    return {"seeded": len(demos)}
