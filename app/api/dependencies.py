from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import AsyncSessionLocal
from fastapi import Header, HTTPException
from app.core.config import settings

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting an async database session.
    The caller is responsible for committing; this dependency only handles cleanup.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

def verify_admin_key(x_admin_key: str = Header(...)):
    """
    Dependency for protecting internal admin endpoints.
    """
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin API key")
    return x_admin_key
