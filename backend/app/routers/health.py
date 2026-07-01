from datetime import datetime, timezone

from fastapi import APIRouter

from app.cache.redis_client import redis_client
from app.config import get_settings
from app.schemas.response import HealthResponse, ReadyResponse

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health():
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/health/ready", response_model=ReadyResponse)
async def ready():
    redis_ok = await redis_client.ping()
    settings = get_settings()
    llm_ok = "ok" if settings.MODEL_API_KEY else "missing_key"
    github_ok = "ok" if settings.GITHUB_TOKEN else "no_token"
    status = "ready" if redis_ok and llm_ok == "ok" else "degraded"
    return ReadyResponse(
        status=status,
        checks={"redis": "ok" if redis_ok else "fail", "llm": llm_ok, "github": github_ok},
    )
