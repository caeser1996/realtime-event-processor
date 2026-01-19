"""API v1 routes."""

from fastapi import APIRouter

from app.api.v1 import events, analytics, health

router = APIRouter(prefix="/api/v1")

router.include_router(events.router, prefix="/events", tags=["events"])
router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
router.include_router(health.router, tags=["health"])
