"""
Task management – create, assign, report, complete.
"""

from typing import Annotated, List, Optional
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.task import Task, TaskAssignment
from app.models.ambassador import DigitalAmbassador
from app.models.geo import GeoHierarchy
from app.services.badges import compute_badges

router = APIRouter()


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    task_type: Optional[str] = None
    priority: str = "medium"
    geo_id: Optional[UUID] = None
    due_at: Optional[datetime] = None
    ambassador_ids: List[UUID] = []
    source_recommendation_id: Optional[UUID] = None


class TaskOut(BaseModel):
    id: str
    title: str
    description: Optional[str]
    task_type: Optional[str]
    priority: str
    status: str
    geo_id: Optional[str]
    geo_name: Optional[str]
    due_at: Optional[datetime]
    created_at: datetime
    assignment_count: int = 0


class AssignmentReport(BaseModel):
    report_text: str
    report_media: List[str] = []


class AssignmentOut(BaseModel):
    id: str
    task_id: str
    task_title: str
    status: str
    assigned_at: datetime
    completed_at: Optional[datetime]
    report_text: Optional[str]


@router.post("/", response_model=TaskOut, status_code=201)
async def create_task(
    payload: TaskCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    task = Task(
        title=payload.title,
        description=payload.description,
        task_type=payload.task_type,
        priority=payload.priority,
        geo_id=payload.geo_id,
        due_at=payload.due_at,
        created_by=current_user.id,
        source_recommendation_id=payload.source_recommendation_id,
        status="open",
    )
    db.add(task)
    await db.flush()

    for amb_id in payload.ambassador_ids:
        amb = await db.get(DigitalAmbassador, amb_id)
        if not amb:
            continue
        assignment = TaskAssignment(task_id=task.id, ambassador_id=amb_id, status="assigned")
        db.add(assignment)
        amb.total_tasks = (amb.total_tasks or 0) + 1

    await db.commit()
    await db.refresh(task)

    geo_name = None
    if task.geo_id:
        g = await db.get(GeoHierarchy, task.geo_id)
        geo_name = g.name if g else None

    return TaskOut(
        id=str(task.id),
        title=task.title,
        description=task.description,
        task_type=task.task_type,
        priority=task.priority,
        status=task.status,
        geo_id=str(task.geo_id) if task.geo_id else None,
        geo_name=geo_name,
        due_at=task.due_at,
        created_at=task.created_at,
        assignment_count=len(payload.ambassador_ids),
    )


@router.get("/", response_model=List[TaskOut])
async def list_tasks(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
):
    q = select(Task).order_by(desc(Task.created_at)).limit(limit)
    if status:
        q = q.where(Task.status == status)
    result = await db.execute(q)
    tasks = result.scalars().all()
    out = []
    for t in tasks:
        geo_name = None
        if t.geo_id:
            g = await db.get(GeoHierarchy, t.geo_id)
            geo_name = g.name if g else None
        # count assignments
        cnt = await db.scalar(
            select(TaskAssignment).where(TaskAssignment.task_id == t.id)
        )
        out.append(TaskOut(
            id=str(t.id),
            title=t.title,
            description=t.description,
            task_type=t.task_type,
            priority=t.priority,
            status=t.status,
            geo_id=str(t.geo_id) if t.geo_id else None,
            geo_name=geo_name,
            due_at=t.due_at,
            created_at=t.created_at,
            assignment_count=0,
        ))
    return out


@router.get("/my", response_model=List[AssignmentOut])
async def my_tasks(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Tasks assigned to the current user (if they are an ambassador)."""
    amb_res = await db.execute(
        select(DigitalAmbassador).where(DigitalAmbassador.user_id == current_user.id)
    )
    amb = amb_res.scalar_one_or_none()
    if not amb:
        return []

    q = (
        select(TaskAssignment, Task)
        .join(Task, TaskAssignment.task_id == Task.id)
        .where(TaskAssignment.ambassador_id == amb.id)
        .order_by(desc(TaskAssignment.assigned_at))
    )
    result = await db.execute(q)
    rows = result.all()
    return [
        AssignmentOut(
            id=str(a.id),
            task_id=str(a.task_id),
            task_title=t.title,
            status=a.status,
            assigned_at=a.assigned_at,
            completed_at=a.completed_at,
            report_text=a.report_text,
        )
        for a, t in rows
    ]


@router.post("/assignments/{assignment_id}/report", response_model=AssignmentOut)
async def submit_report(
    assignment_id: UUID,
    payload: AssignmentReport,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    assignment = await db.get(TaskAssignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    amb = await db.get(DigitalAmbassador, assignment.ambassador_id)
    if not amb or amb.user_id != current_user.id:
        # allow coordinators too later; for now owner only
        roles = [r.name for r in current_user.roles]
        if "super_admin" not in roles and "volunteer_coordinator" not in roles:
            raise HTTPException(status_code=403, detail="Not your assignment")

    assignment.report_text = payload.report_text
    assignment.report_media = payload.report_media
    assignment.status = "completed"
    assignment.completed_at = datetime.now(timezone.utc)

    if amb:
        amb.completed_tasks = (amb.completed_tasks or 0) + 1
        # simple score: +5 per completed task, cap 100
        amb.performance_score = min(100, float(amb.performance_score or 0) + 5)
        amb.badges = compute_badges(
            amb.completed_tasks or 0,
            float(amb.performance_score or 0),
            amb.badges if isinstance(amb.badges, list) else [],
        )

    await db.commit()
    task = await db.get(Task, assignment.task_id)
    return AssignmentOut(
        id=str(assignment.id),
        task_id=str(assignment.task_id),
        task_title=task.title if task else "",
        status=assignment.status,
        assigned_at=assignment.assigned_at,
        completed_at=assignment.completed_at,
        report_text=assignment.report_text,
    )
