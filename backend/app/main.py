from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.cache.redis_client import redis_client
from app.config import get_settings
from app.middleware.rate_limit import rate_limit_middleware
from app.routers import analyze, health, report, stream
from app.utils.exceptions import RepoAgentError
from common.logger import my_logger

logger = my_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    await redis_client.connect()
    logger.info("RepoAgent backend started")
    yield
    await redis_client.close()
    logger.info("RepoAgent backend stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="RepoAgent", version=settings.APP_VERSION, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def apply_rate_limit(request: Request, call_next):
        return await rate_limit_middleware(request, call_next)

    @app.exception_handler(RepoAgentError)
    async def repo_agent_error_handler(request: Request, exc: RepoAgentError):
        return JSONResponse(
            status_code=400 if exc.code < 5000 else 500,
            content={"code": exc.code, "message": exc.message, "stage": exc.stage},
        )

    app.include_router(analyze.router)
    app.include_router(stream.router)
    app.include_router(report.router)
    app.include_router(health.router)

    return app


app = create_app()
