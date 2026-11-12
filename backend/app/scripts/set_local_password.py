"""Set a local password for one existing TLMS account.

The target email and plaintext password must be supplied through environment
variables. The plaintext value is never printed or stored.
"""
import asyncio
import os

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.services.local_auth import LocalAuthService


async def main() -> None:
    email = os.environ.get("LOCAL_AUTH_TARGET_EMAIL", "").strip().lower()
    password = os.environ.get("LOCAL_AUTH_TARGET_PASSWORD", "")
    if not email or not password:
        raise SystemExit(
            "LOCAL_AUTH_TARGET_EMAIL and LOCAL_AUTH_TARGET_PASSWORD are required"
        )

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(func.lower(User.email) == email))
        user = result.scalar_one_or_none()
        if user is None:
            raise SystemExit(f"No TLMS account found for {email}")

        user.password_hash = LocalAuthService.hash_password(password)
        await db.commit()
        print(f"Local password updated for {email}")


if __name__ == "__main__":
    asyncio.run(main())
