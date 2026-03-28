"""Main entry point for Scheduler Agent."""

import asyncio
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure 'src' is importable when running from the scheduler-agent root folder
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger

from src.config.settings import settings
from src.api.routes import router
from src.agent.scheduler import scheduler_agent
from src.messaging.redis_client import redis_client

_START_TIME = time.time()

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

logger.remove()
logger.add(
    sys.stderr,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan> - "
        "<level>{message}</level>"
    ),
    level=settings.log_level,
)
logger.add(
    settings.log_file,
    rotation="10 MB",
    retention="7 days",
    level=settings.log_level,
)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start and stop background task listener alongside the FastAPI process."""
    # ---- Startup --------------------------------------------------------
    logger.info("=" * 60)
    logger.info("⏰ Scheduler Agent Starting")
    logger.info("=" * 60)
    logger.info(f"Environment : {settings.environment}")
    logger.info(f"API         : http://{settings.api_host}:{settings.api_port}")
    logger.info(f"Redis       : {settings.redis_host}:{settings.redis_port}")
    logger.info(f"n8n Webhooks: {settings.n8n_webhook_base_url}")
    logger.info(f"Log file    : {settings.log_file}")
    logger.info("=" * 60)

    # Start the Redis stream listener as a non-blocking background task
    listener_task = asyncio.create_task(scheduler_agent.start_listening())

    # Brief pause so listener initialises before accepting HTTP traffic
    await asyncio.sleep(0.5)
    logger.info("✅ Scheduler Agent API ready – accepting requests")

    yield

    # ---- Shutdown -------------------------------------------------------
    logger.info("👋 Scheduler Agent shutting down")
    listener_task.cancel()
    try:
        await listener_task
    except asyncio.CancelledError:
        pass


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Scheduler Agent",
    description=(
        "Deterministic scheduling execution agent for AgenticHR. "
        "Handles Google Calendar / Meet operations via n8n webhooks."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/api/v1", tags=["scheduler"])


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    """Optional API-key guard. Skipped when AGENTHR_API_KEY is not configured."""
    skip_prefixes = ("/api/v1/health", "/metrics", "/docs", "/openapi.json", "/")
    if settings.api_key and not any(request.url.path.startswith(p) for p in skip_prefixes):
        key = request.headers.get("X-API-Key", "")
        if key != settings.api_key:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)


@app.get("/metrics")
async def get_metrics():
    """Runtime metrics for the Scheduler Agent."""
    return {
        "agent": "scheduler_agent",
        "uptime_seconds": int(time.time() - _START_TIME),
        "redis_connected": redis_client.health_check(),
        "stream_info": redis_client.get_stream_info("scheduler_agent")
    }


@app.get("/")
async def root():
    """Root endpoint – basic agent identity."""
    return {
        "agent": "scheduler_agent",
        "version": "1.0.0",
        "status": "running",
        "description": "Deterministic scheduling execution agent for AgenticHR",
        "endpoints": {
            "health": "/api/v1/health",
            "status": "/api/v1/status",
            "execute_task": "/api/v1/execute-task",
            "cache": "/api/v1/cache",
        },
    }


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        reload=(settings.environment == "development"),
        log_level=settings.log_level.lower(),
    )
