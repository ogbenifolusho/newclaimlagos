"""
Geography endpoints – hierarchy & boundaries from PostGIS.
"""

from typing import Annotated, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.geo import GeoHierarchy

router = APIRouter()


class GeoNode(BaseModel):
    id: str
    level: str
    name: str
    code: Optional[str] = None
    parent_id: Optional[str] = None
    is_placeholder: bool = True
    source: str = "public"


@router.get("/hierarchy", response_model=List[GeoNode])
async def get_hierarchy(
    db: Annotated[AsyncSession, Depends(get_db)],
    level: Optional[str] = Query(None),
    parent_id: Optional[UUID] = None,
    limit: int = Query(500, le=2000),
):
    q = select(GeoHierarchy)
    if level:
        q = q.where(GeoHierarchy.level == level)
    if parent_id:
        q = q.where(GeoHierarchy.parent_id == parent_id)
    q = q.order_by(GeoHierarchy.name).limit(limit)
    result = await db.execute(q)
    nodes = result.scalars().all()
    return [
        GeoNode(
            id=str(n.id),
            level=n.level,
            name=n.name,
            code=n.code,
            parent_id=str(n.parent_id) if n.parent_id else None,
            is_placeholder=n.is_placeholder,
            source=n.source,
        )
        for n in nodes
    ]


@router.get("/boundaries/{geo_id}")
async def get_boundary(
    geo_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(
            GeoHierarchy.id,
            GeoHierarchy.name,
            GeoHierarchy.level,
            GeoHierarchy.is_placeholder,
            func.ST_AsGeoJSON(GeoHierarchy.geometry).label("geojson"),
            func.ST_AsGeoJSON(GeoHierarchy.centroid).label("centroid"),
        ).where(GeoHierarchy.id == geo_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Geo node not found")
    return {
        "type": "Feature",
        "properties": {
            "id": str(row.id),
            "name": row.name,
            "level": row.level,
            "is_placeholder": row.is_placeholder,
        },
        "geometry": row.geojson,
        "centroid": row.centroid,
    }


@router.get("/stats")
async def geo_stats(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(GeoHierarchy.level, func.count()).group_by(GeoHierarchy.level)
    )
    counts = {level: count for level, count in result.all()}
    return {"counts_by_level": counts, "note": "Public sources – placeholders until official data loaded"}
