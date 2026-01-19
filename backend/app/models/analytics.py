"""Analytics data models."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TimeSeriesData(BaseModel):
    """Time series data point."""

    timestamp: datetime
    value: float
    label: Optional[str] = None


class TimeSeriesResponse(BaseModel):
    """Response containing time series data."""

    metric: str
    interval: str
    data: List[TimeSeriesData]
    total: float
    average: float


class AggregatedMetrics(BaseModel):
    """Aggregated metrics for a time period."""

    period_start: datetime
    period_end: datetime
    total_events: int
    events_per_second: float
    unique_users: int
    unique_sessions: int
    events_by_type: Dict[str, int]
    top_pages: List[Dict[str, Any]]
    error_rate: float


class RealTimeMetrics(BaseModel):
    """Real-time metrics snapshot."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    events_last_minute: int = Field(0, description="Events in the last minute")
    events_last_hour: int = Field(0, description="Events in the last hour")
    active_users: int = Field(0, description="Currently active users")
    active_sessions: int = Field(0, description="Currently active sessions")
    events_per_second: float = Field(0.0, description="Current event rate")
    processing_lag_ms: float = Field(0.0, description="Processing lag in milliseconds")
    kafka_lag: int = Field(0, description="Kafka consumer lag")
    error_count: int = Field(0, description="Errors in the last hour")
    top_event_types: List[Dict[str, Any]] = Field(
        default_factory=list, description="Top event types"
    )


class TopEvents(BaseModel):
    """Top events analysis."""

    event_type: str
    count: int
    percentage: float
    trend: str  # "up", "down", "stable"
    change_percent: float


class UserAnalytics(BaseModel):
    """User-level analytics."""

    user_id: str
    total_events: int
    first_seen: datetime
    last_seen: datetime
    session_count: int
    favorite_pages: List[str]
    conversion_events: int


class DashboardSummary(BaseModel):
    """Complete dashboard summary."""

    realtime: RealTimeMetrics
    hourly_trend: List[TimeSeriesData]
    event_distribution: List[TopEvents]
    user_activity: Dict[str, Any]
    system_health: Dict[str, Any]
