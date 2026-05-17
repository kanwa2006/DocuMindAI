from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
import redis.asyncio as redis
from app.core.config import settings

router = APIRouter()

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    status = {"api": "ok", "db": "unknown", "redis": "unknown"}
    
    # Check DB
    try:
        await db.execute(text("SELECT 1"))
        status["db"] = "ok"
    except Exception as e:
        status["db"] = f"error: {str(e)}"
        
    # Check Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        status["redis"] = "ok"
        await r.close()
    except Exception as e:
        status["redis"] = f"error: {str(e)}"

    if status["db"] != "ok" or status["redis"] != "ok":
        raise HTTPException(status_code=503, detail=status)
        
    return status
