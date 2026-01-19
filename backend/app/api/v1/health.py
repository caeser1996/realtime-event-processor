"""Health check endpoints."""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter

from app.core.config import settings
from app.core.logging import get_logger
from app.kafka.producer import get_producer
from app.clickhouse.client import get_clickhouse_client

logger = get_logger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.

    Returns the service status and basic information.
    Used by load balancers and container orchestration.
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/ready")
async def readiness_check() -> Dict[str, Any]:
    """
    Readiness check for Kubernetes.

    Verifies all dependencies are available before accepting traffic.
    """
    checks = {
        "kafka": False,
        "clickhouse": False,
    }
    errors = []

    # Check Kafka
    try:
        producer = await get_producer()
        checks["kafka"] = producer.is_connected
    except Exception as e:
        errors.append(f"Kafka: {str(e)}")

    # Check ClickHouse
    try:
        clickhouse = await get_clickhouse_client()
        checks["clickhouse"] = clickhouse.is_connected
    except Exception as e:
        errors.append(f"ClickHouse: {str(e)}")

    all_healthy = all(checks.values())

    return {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks,
        "errors": errors if errors else None,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/live")
async def liveness_check() -> Dict[str, str]:
    """
    Liveness check for Kubernetes.

    Simple check to verify the service is running.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
    }
