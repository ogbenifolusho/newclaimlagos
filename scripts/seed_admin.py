#!/usr/bin/env python3
"""
Create the initial Super Administrator account.
Run once after DB is up:

  docker compose exec api python /app/../scripts/seed_admin.py
  or
  DATABASE_URL=... python scripts/seed_admin.py
"""

import asyncio
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.user import User, Role
from app.core.security import get_password_hash

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@claimlagos.local")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ChangeMeImmediately1!")
ADMIN_NAME = os.getenv("ADMIN_NAME", "Super Administrator")


async def main():
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(User).where(User.email == ADMIN_EMAIL))
        if existing.scalar_one_or_none():
            print(f"Admin already exists: {ADMIN_EMAIL}")
            return

        role_res = await db.execute(select(Role).where(Role.name == "super_admin"))
        role = role_res.scalar_one_or_none()
        if not role:
            print("ERROR: super_admin role not found. Did init-db.sql run?")
            return

        user = User(
            email=ADMIN_EMAIL,
            full_name=ADMIN_NAME,
            hashed_password=get_password_hash(ADMIN_PASSWORD),
            is_active=True,
            is_verified=True,
        )
        user.roles.append(role)
        db.add(user)
        await db.commit()
        print(f"✅ Super Admin created")
        print(f"   Email:    {ADMIN_EMAIL}")
        print(f"   Password: {ADMIN_PASSWORD}")
        print("   CHANGE THE PASSWORD IMMEDIATELY AFTER FIRST LOGIN.")


if __name__ == "__main__":
    asyncio.run(main())
