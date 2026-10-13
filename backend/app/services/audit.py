"""Audit log helper – write significant actions to audit_logs table."""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


async def write_audit(
    db: AsyncSession,
    *,
    user_id: UUID | None,
    action: str,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
):
    await db.execute(
        text("""
            INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details, ip_address)
            VALUES (:user_id, :action, :resource_type, :resource_id, CAST(:details AS jsonb), CAST(:ip AS inet))
        """),
        {
            "user_id": str(user_id) if user_id else None,
            "action": action,
            "resource_type": resource_type,
            "resource_id": str(resource_id) if resource_id else None,
            "details": __import__("json").dumps(details or {}),
            "ip": ip_address,
        },
    )
    # caller commits
