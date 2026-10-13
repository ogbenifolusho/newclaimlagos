"""
Social ingestion – PLACEHOLDER connectors for X, Meta, YouTube, Google, TikTok.
Credentials come from env; when empty, demo/synthetic ingest is used for testing.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4
import random

from app.core.config import settings
from app.services.intelligence import (
    classify_sentiment,
    classify_topics,
    detect_language,
    match_keywords,
    bot_heuristic,
)


PLATFORMS = ["x", "facebook", "instagram", "youtube", "tiktok"]


def platform_configured(platform: str) -> bool:
    mapping = {
        "x": bool(settings.X_BEARER_TOKEN),
        "facebook": bool(settings.META_ACCESS_TOKEN),
        "instagram": bool(settings.META_ACCESS_TOKEN),
        "youtube": bool(settings.YOUTUBE_API_KEY),
        "tiktok": bool(settings.TIKTOK_ACCESS_TOKEN),
    }
    return mapping.get(platform, False)


async def fetch_platform_posts(platform: str, keywords: List[str], limit: int = 20) -> List[dict]:
    """
    Real API calls would go here.
    Until credentials are provided, return synthetic posts for pipeline testing.
    """
    if platform_configured(platform):
        # Placeholder for real HTTP calls
        # e.g. httpx get Twitter recent search, Meta Graph, etc.
        return []

    # Synthetic demo data so Listen module is testable offline
    samples = [
        "Lagos roads are seeing real progress this year – hope it continues",
        "Traffic in Ikeja is still a nightmare. When will transport improve?",
        "Great job on the new BRT corridor. Proud of the development",
        "Corruption allegations need investigation – citizens deserve accountability",
        "Unemployment among youth in Alimosho is too high",
        "Healthcare centres need more doctors and medicine",
        "Education standards must improve in public schools",
        "Security in Lagos Island has been better lately",
        "Housing rents are crushing families across the state",
        "Governance should focus on delivery not politics",
    ]
    posts = []
    for i in range(min(limit, len(samples))):
        text = samples[i]
        if keywords:
            # bias content to include a keyword sometimes
            if random.random() > 0.4:
                text = f"{text} #{keywords[0].replace(' ', '')}"
        sentiment, score = classify_sentiment(text)
        posts.append({
            "platform": platform,
            "external_id": f"demo-{platform}-{uuid4().hex[:8]}",
            "author_handle": f"user_{random.randint(100,9999)}",
            "content": text,
            "sentiment": sentiment,
            "sentiment_score": score,
            "topics": classify_topics(text),
            "language": detect_language(text),
            "engagement": {"likes": random.randint(0, 500), "shares": random.randint(0, 50)},
            "created_at": datetime.now(timezone.utc),
            "raw_payload": {"source": "synthetic_placeholder"},
        })
    return posts


async def process_post(raw: dict, active_keywords: List[str]) -> dict:
    content = raw.get("content") or ""
    sentiment, score = classify_sentiment(content)
    topics = classify_topics(content)
    matched = match_keywords(content, active_keywords)
    is_bot = bot_heuristic(raw.get("author_handle"), content, raw.get("engagement"))
    return {
        **raw,
        "sentiment": sentiment,
        "sentiment_score": score,
        "topics": topics,
        "language": detect_language(content),
        "matched_keywords": matched,
        "is_bot_suspect": is_bot,
    }
