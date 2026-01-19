"""Event data models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Supported event types."""

    USER_ACTION = "user_action"
    PAGE_VIEW = "page_view"
    CLICK = "click"
    FORM_SUBMIT = "form_submit"
    PURCHASE = "purchase"
    ERROR = "error"
    CUSTOM = "custom"


class EventCreate(BaseModel):
    """Schema for creating a new event."""

    event_type: EventType = Field(..., description="Type of event")
    user_id: Optional[str] = Field(None, description="User identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event payload")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Event metadata")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "event_type": "user_action",
                    "user_id": "user123",
                    "session_id": "sess456",
                    "payload": {"action": "click", "element": "signup_button"},
                    "metadata": {"page": "/home", "referrer": "google.com"},
                }
            ]
        }
    }


class Event(BaseModel):
    """Complete event model."""

    id: UUID = Field(default_factory=uuid4, description="Unique event identifier")
    event_type: EventType = Field(..., description="Type of event")
    user_id: Optional[str] = Field(None, description="User identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event payload")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Event metadata")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Event timestamp"
    )
    processed_at: Optional[datetime] = Field(None, description="Processing timestamp")
    source_ip: Optional[str] = Field(None, description="Source IP address")
    user_agent: Optional[str] = Field(None, description="User agent string")

    model_config = {"from_attributes": True}


class EventResponse(BaseModel):
    """Response model for event creation."""

    id: UUID
    event_type: EventType
    timestamp: datetime
    status: str = "accepted"
    message: str = "Event queued for processing"


class EventBatch(BaseModel):
    """Batch of events for bulk operations."""

    events: List[EventCreate] = Field(..., min_length=1, max_length=1000)


class EventStats(BaseModel):
    """Event statistics model."""

    total_events: int = Field(..., description="Total number of events")
    events_by_type: Dict[str, int] = Field(
        default_factory=dict, description="Events grouped by type"
    )
    unique_users: int = Field(..., description="Number of unique users")
    unique_sessions: int = Field(..., description="Number of unique sessions")
    time_range: Dict[str, datetime] = Field(
        default_factory=dict, description="Time range of events"
    )


class GenerateEventsRequest(BaseModel):
    """Request to generate sample events."""

    count: int = Field(default=100, ge=1, le=10000, description="Number of events")
    event_type: Optional[EventType] = Field(
        None, description="Event type (random if not specified)"
    )
    user_count: int = Field(
        default=10, ge=1, le=1000, description="Number of unique users"
    )
    delay_ms: int = Field(
        default=0, ge=0, le=1000, description="Delay between events in milliseconds"
    )
