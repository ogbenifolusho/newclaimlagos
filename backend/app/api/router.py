from fastapi import APIRouter

from app.api import (
    health, auth, geo, ambassadors, situation_room,
    tasks, recommendations, content, campaign, listen,
    ads, influence, create_mod, intelligence, reports,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(geo.router, prefix="/geo", tags=["Geography"])
api_router.include_router(ambassadors.router, prefix="/ambassadors", tags=["Digital Ambassadors"])
api_router.include_router(situation_room.router, prefix="/situation-room", tags=["Situation Room"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["Recommendations"])
api_router.include_router(content.router, prefix="/content", tags=["Content Packs"])
api_router.include_router(campaign.router, prefix="/campaign", tags=["Campaign"])
api_router.include_router(listen.router, prefix="/listen", tags=["Listen"])
api_router.include_router(ads.router, prefix="/ads", tags=["Digital Ads"])
api_router.include_router(influence.router, prefix="/influence", tags=["Amplify & Influence"])
api_router.include_router(create_mod.router, prefix="/create", tags=["CREATE"])
api_router.include_router(intelligence.router, prefix="/intelligence", tags=["Intelligence"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
