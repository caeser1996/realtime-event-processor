"""Analytics API endpoints."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.core.logging import get_logger
from app.clickhouse.client import get_clickhouse_client
from app.models.analytics import RealTimeMetrics

logger = get_logger(__name__)
router = APIRouter()


@router.get("/stats")
async def get_event_stats(
    start_time: Optional[datetime] = Query(
        None, description="Start time (defaults to 24h ago)"
    ),
    end_time: Optional[datetime] = Query(
        None, description="End time (defaults to now)"
    ),
) -> Dict[str, Any]:
    """
    Get aggregated event statistics for a time period.

    Returns total events, unique users, unique sessions, and breakdown by event type.
    """
    try:
        clickhouse = await get_clickhouse_client()
        stats = await clickhouse.get_event_stats(
            start_time=start_time,
            end_time=end_time,
        )
        return stats

    except Exception as e:
        logger.error("Failed to get event stats", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve event statistics",
        )


@router.get("/realtime", response_model=RealTimeMetrics)
async def get_realtime_metrics() -> RealTimeMetrics:
    """
    Get real-time metrics for the dashboard.

    Returns current event rates, active users, and top event types.
    Designed for polling at 5-10 second intervals.
    """
    try:
        clickhouse = await get_clickhouse_client()
        metrics = await clickhouse.get_realtime_metrics()

        return RealTimeMetrics(
            timestamp=datetime.fromisoformat(metrics["timestamp"]),
            events_last_minute=metrics["events_last_minute"],
            events_last_hour=metrics["events_last_hour"],
            active_users=metrics["active_users"],
            active_sessions=metrics["active_sessions"],
            events_per_second=metrics["events_per_second"],
            error_count=metrics["error_count"],
            top_event_types=metrics["top_event_types"],
        )

    except Exception as e:
        logger.error("Failed to get realtime metrics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve real-time metrics",
        )


@router.get("/timeseries")
async def get_time_series(
    interval: str = Query(
        "1h",
        description="Time interval: 1m, 5m, 15m, 1h, 1d",
        regex="^(1m|5m|15m|1h|1d)$",
    ),
    start_time: Optional[datetime] = Query(
        None, description="Start time (defaults to 24h ago)"
    ),
    end_time: Optional[datetime] = Query(
        None, description="End time (defaults to now)"
    ),
) -> Dict[str, Any]:
    """
    Get time series data for charts.

    Returns event counts and unique users grouped by the specified interval.
    """
    try:
        clickhouse = await get_clickhouse_client()
        data = await clickhouse.get_time_series(
            interval=interval,
            start_time=start_time,
            end_time=end_time,
        )

        # Calculate totals
        total_events = sum(d["event_count"] for d in data)
        avg_events = total_events / len(data) if data else 0

        return {
            "interval": interval,
            "data": data,
            "summary": {
                "total_events": total_events,
                "average_per_interval": round(avg_events, 2),
                "data_points": len(data),
            },
        }

    except Exception as e:
        logger.error("Failed to get time series", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve time series data",
        )


@router.get("/top-events")
async def get_top_events(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    limit: int = Query(10, ge=1, le=100, description="Number of top events"),
) -> Dict[str, Any]:
    """
    Get top events by count for a time period.
    """
    try:
        clickhouse = await get_clickhouse_client()
        start_time = datetime.utcnow() - timedelta(hours=hours)

        query = f"""
        SELECT
            event_type,
            count() AS event_count,
            uniqExact(user_id) AS unique_users,
            uniqExact(session_id) AS unique_sessions
        FROM events
        WHERE timestamp >= '{start_time.isoformat()}'
        GROUP BY event_type
        ORDER BY event_count DESC
        LIMIT {limit}
        """

        result = clickhouse._client.query(query)

        events = []
        total = sum(row[1] for row in result.result_rows)

        for row in result.result_rows:
            events.append({
                "event_type": row[0],
                "count": row[1],
                "percentage": round((row[1] / total * 100) if total > 0 else 0, 2),
                "unique_users": row[2],
                "unique_sessions": row[3],
            })

        return {
            "time_window_hours": hours,
            "total_events": total,
            "events": events,
        }

    except Exception as e:
        logger.error("Failed to get top events", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve top events",
        )


@router.get("/users/{user_id}")
async def get_user_analytics(
    user_id: str,
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
) -> Dict[str, Any]:
    """
    Get analytics for a specific user.
    """
    try:
        clickhouse = await get_clickhouse_client()
        start_time = datetime.utcnow() - timedelta(hours=hours)

        query = f"""
        SELECT
            count() AS total_events,
            uniqExact(session_id) AS session_count,
            min(timestamp) AS first_event,
            max(timestamp) AS last_event,
            groupArray(DISTINCT event_type) AS event_types
        FROM events
        WHERE user_id = '{user_id}'
          AND timestamp >= '{start_time.isoformat()}'
        """

        result = clickhouse._client.query(query)

        if not result.result_rows or result.result_rows[0][0] == 0:
            raise HTTPException(status_code=404, detail="User not found")

        row = result.result_rows[0]

        return {
            "user_id": user_id,
            "time_window_hours": hours,
            "total_events": row[0],
            "session_count": row[1],
            "first_event": row[2].isoformat() if row[2] else None,
            "last_event": row[3].isoformat() if row[3] else None,
            "event_types": row[4] if row[4] else [],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get user analytics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve user analytics",
        )


@router.get("/dashboard")
async def get_dashboard_data() -> Dict[str, Any]:
    """
    Get all data needed for the dashboard in a single call.

    Combines real-time metrics, time series, and top events for efficient loading.
    """
    try:
        clickhouse = await get_clickhouse_client()

        # Get all data
        realtime = await clickhouse.get_realtime_metrics()
        timeseries = await clickhouse.get_time_series(interval="1h")
        stats = await clickhouse.get_event_stats()

        return {
            "realtime": realtime,
            "timeseries": {
                "interval": "1h",
                "data": timeseries,
            },
            "stats": stats,
            "updated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("Failed to get dashboard data", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve dashboard data",
        )
