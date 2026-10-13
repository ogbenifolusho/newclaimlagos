"""
Campaign calendar, election countdown, system config.
"""

from typing import Annotated, List, Optional
from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User

router = APIRouter()

# In-memory config for VPS simplicity; move to DB table later
_CAMPAIGN_CONFIG = {
    "election_date": "2027-02-20",  # placeholder – set real date
    "campaign_name": "PBAT-KOH 2027",
    "state": "Lagos",
}


class CalendarEvent(BaseModel):
    id: str
    title: str
    event_date: date
    event_type: str  # rally | media | training | deadline | other
    geo_name: Optional[str] = None


class CampaignConfig(BaseModel):
    election_date: str
    campaign_name: str
    state: str
    countdown_days: int


@router.get("/config", response_model=CampaignConfig)
async def get_config():
    try:
        ed = date.fromisoformat(_CAMPAIGN_CONFIG["election_date"])
        days = (ed - date.today()).days
    except Exception:
        days = 0
    return CampaignConfig(
        election_date=_CAMPAIGN_CONFIG["election_date"],
        campaign_name=_CAMPAIGN_CONFIG["campaign_name"],
        state=_CAMPAIGN_CONFIG["state"],
        countdown_days=max(0, days),
    )


@router.put("/config")
async def update_config(
    election_date: Optional[str] = None,
    campaign_name: Optional[str] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    if election_date:
        _CAMPAIGN_CONFIG["election_date"] = election_date
    if campaign_name:
        _CAMPAIGN_CONFIG["campaign_name"] = campaign_name
    return await get_config()


@router.get("/calendar", response_model=List[CalendarEvent])
async def get_calendar():
    """Placeholder calendar events – replace with DB table."""
    return [
        CalendarEvent(
            id="evt-1",
            title="New Media Directorate weekly review",
            event_date=date.today(),
            event_type="media",
        ),
        CalendarEvent(
            id="evt-2",
            title="Ambassador training – Ikeja cluster",
            event_date=date.today(),
            event_type="training",
            geo_name="Ikeja",
        ),
    ]
