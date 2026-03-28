"""Main entry point for Provisioning Agent."""

import asyncio
import sys
import time
from pathlib import Path
from contextlib import asynccontextmanager

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger
import uvicorn

from src.config.settings import settings
from src.api.routes import router
from src.agent.provisioning import provisioning_agent
from src.messaging.redis_client import redis_client

_START_TIME = time.time()


# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=settings.log_level
)
logger.add(
    settings.log_file,
    rotation="10 MB",
    retention="7 days",
    level=settings.log_level
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("=" * 60)
    logger.info("🚀 Provisioning Agent Starting")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"API: http://{settings.api_host}:{settings.api_port}")
    logger.info(f"Redis: {settings.redis_host}:{settings.redis_port}")
    logger.info(f"n8n Webhooks: {settings.n8n_webhook_base_url}")
    logger.info(f"Log file: {settings.log_file}")
    logger.info("=" * 60)
    
    # Start listener as background task (non-blocking)
    listener_task = asyncio.create_task(provisioning_agent.start_listening())
    
    # Give listener a moment to start
    await asyncio.sleep(0.5)
    logger.info("✅ API ready - accepting requests on port 8003")
    
    yield
    
    # Shutdown
    logger.info("👋 Provisioning Agent shutting down")
    listener_task.cancel()
    try:
        await listener_task
    except asyncio.CancelledError:
        pass


# Create FastAPI app with lifespan
app = FastAPI(
    title="Provisioning Agent",
    description="Deterministic execution agent for provisioning tasks in AgenticHR",
    version="1.0.0",
    lifespan=lifespan
)

# Include routes
app.include_router(router, prefix="/api/v1", tags=["provisioning"])


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
    """Runtime metrics for the Provisioning Agent."""
    return {
        "agent": "provisioning_agent",
        "uptime_seconds": int(time.time() - _START_TIME),
        "redis_connected": redis_client.health_check(),
        "stream_info": redis_client.get_stream_info("provisioning_agent")
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "agent": "provisioning_agent",
        "version": "1.0.0",
        "status": "running",
        "mode": "deterministic",
        "description": "Deterministic execution agent for provisioning tasks",
        "endpoints": {
            "health": "/api/v1/health",
            "status": "/api/v1/status",
            "docs": "/docs"
        }
    }


def main():
    """Run the Provisioning Agent."""
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        reload=settings.environment == "development"
    )


if __name__ == "__main__":
    main()
