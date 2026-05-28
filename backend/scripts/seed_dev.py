"""
Seed script — creates a dev user for immediate local testing.
Run from: cd backend && python scripts/seed_dev.py

Login credentials after running:
  Email:    dev@test.com
  Password: devpass123
"""
import asyncio
import sys
import os

# Allow importing from app/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from uuid import uuid4
from datetime import datetime
from sqlalchemy.future import select

from app.db.session import AsyncSessionLocal
from app.models.org import User, UserRole
from app.core.security import hash_password


async def seed():
    async with AsyncSessionLocal() as db:
        # Check if dev user already exists
        result = await db.execute(select(User).where(User.email == "dev@test.com"))
        existing = result.scalar_one_or_none()

        if existing:
            print("✓ Dev user already exists — no action needed.")
            print("  Email:    dev@test.com")
            print("  Password: devpass123")
            return

        user_id = uuid4()
        user = User(
            id=user_id,
            email="dev@test.com",
            hashed_password=hash_password("devpass123"),
            full_name="Dev User",
            workspace_id="general",
            is_active=True,
            created_at=datetime.utcnow(),
        )
        db.add(user)

        # Assign admin role so all endpoints are accessible during testing
        role = UserRole(
            id=uuid4(),
            user_id=user_id,
            role="admin",
            created_at=datetime.utcnow(),
        )
        db.add(role)

        await db.commit()
        print("✓ Dev user created successfully.")
        print("  Email:    dev@test.com")
        print("  Password: devpass123")
        print("  Role:     admin")
        print("  Workspace: general")


if __name__ == "__main__":
    asyncio.run(seed())
