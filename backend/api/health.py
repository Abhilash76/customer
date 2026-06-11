from fastapi import APIRouter
from db.postgres import postgres_db
from db.redis import redis_cache

router = APIRouter()

@router.get("/health")
async def health_check():
    """Verify backend system connectivity."""
    postgres_status = "unhealthy"
    redis_status = "unhealthy"
    
    # Check Postgres
    if postgres_db.pool:
        try:
            await postgres_db.fetchval("SELECT 1")
            postgres_status = "healthy"
        except Exception:
            pass
            
    # Check Redis
    if redis_cache.client:
        try:
            await redis_cache.client.ping()
            redis_status = "healthy"
        except Exception:
            pass
            
    overall = "healthy" if postgres_status == "healthy" and redis_status == "healthy" else "degraded"
    
    return {
        "status": overall,
        "version": "1.0.0",
        "dependencies": {
            "postgres": postgres_status,
            "redis": redis_status
        }
    }
