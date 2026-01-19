"""FastAPI application entry point."""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.api.v1 import router as api_router
from app.api.websocket import router as websocket_router, manager
from app.kafka.producer import get_producer, close_producer
from app.clickhouse.client import get_clickhouse_client, close_clickhouse_client

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    logger.info(
        "Starting application",
        app_name=settings.app_name,
        environment=settings.environment,
    )

    # Initialize connections
    try:
        await get_producer()
        logger.info("Kafka producer initialized")
    except Exception as e:
        logger.error("Failed to initialize Kafka producer", error=str(e))

    try:
        await get_clickhouse_client()
        logger.info("ClickHouse client initialized")
    except Exception as e:
        logger.error("Failed to initialize ClickHouse client", error=str(e))

    # Start WebSocket broadcast loop in background
    broadcast_task = asyncio.create_task(manager.start_broadcast_loop(interval=5.0))

    yield

    # Cleanup
    logger.info("Shutting down application")

    broadcast_task.cancel()
    try:
        await broadcast_task
    except asyncio.CancelledError:
        pass

    await close_producer()
    await close_clickhouse_client()

    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Real-time event processing with Kafka, ClickHouse, and FastAPI",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Prometheus metrics
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Mount Prometheus metrics app
metrics_app = make_asgi_app()
app.mount("/prometheus", metrics_app)

# Include routers
app.include_router(api_router)
app.include_router(websocket_router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
    }


@app.get("/health")
async def health():
    """Health check endpoint (shortcut)."""
    from app.api.v1.health import health_check
    return await health_check()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=not settings.is_production,
        log_level=settings.log_level.lower(),
    )
