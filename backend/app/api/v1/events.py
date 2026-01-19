"""Event API endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request, BackgroundTasks
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import get_logger
from app.kafka.producer import get_producer
from app.clickhouse.client import get_clickhouse_client
from app.models.events import (
    Event,
    EventCreate,
    EventResponse,
    EventBatch,
    EventType,
    GenerateEventsRequest,
)
from app.services.event_generator import EventGenerator

logger = get_logger(__name__)
router = APIRouter()


class EventsListResponse(BaseModel):
    """Response for events list endpoint."""

    events: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int


@router.post("", response_model=EventResponse, status_code=202)
async def create_event(
    event: EventCreate,
    request: Request,
    background_tasks: BackgroundTasks,
) -> EventResponse:
    """
    Create a new event.

    The event is validated, enriched with metadata, and sent to Kafka
    for asynchronous processing.
    """
    event_id = uuid4()
    timestamp = datetime.utcnow()

    # Build complete event
    complete_event = {
        "id": str(event_id),
        "event_type": event.event_type.value,
        "user_id": event.user_id,
        "session_id": event.session_id,
        "payload": event.payload,
        "metadata": event.metadata,
        "timestamp": timestamp.isoformat(),
        "source_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }

    # Send to Kafka
    try:
        producer = await get_producer()
        await producer.send(
            topic=settings.kafka_events_topic,
            value=complete_event,
            key=event.user_id or str(event_id),
        )
    except Exception as e:
        logger.error("Failed to send event to Kafka", error=str(e))
        raise HTTPException(
            status_code=503,
            detail="Event queue temporarily unavailable",
        )

    logger.info(
        "Event created",
        event_id=str(event_id),
        event_type=event.event_type.value,
    )

    return EventResponse(
        id=event_id,
        event_type=event.event_type,
        timestamp=timestamp,
        status="accepted",
        message="Event queued for processing",
    )


@router.post("/batch", response_model=Dict[str, Any], status_code=202)
async def create_events_batch(
    batch: EventBatch,
    request: Request,
) -> Dict[str, Any]:
    """
    Create multiple events in a batch.

    All events are validated and sent to Kafka together for efficient processing.
    """
    timestamp = datetime.utcnow()
    source_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    events_to_send = []
    event_ids = []

    for event in batch.events:
        event_id = uuid4()
        event_ids.append(str(event_id))

        events_to_send.append({
            "id": str(event_id),
            "event_type": event.event_type.value,
            "user_id": event.user_id,
            "session_id": event.session_id,
            "payload": event.payload,
            "metadata": event.metadata,
            "timestamp": timestamp.isoformat(),
            "source_ip": source_ip,
            "user_agent": user_agent,
        })

    try:
        producer = await get_producer()
        await producer.send_batch(
            topic=settings.kafka_events_topic,
            messages=events_to_send,
        )
    except Exception as e:
        logger.error("Failed to send batch to Kafka", error=str(e))
        raise HTTPException(
            status_code=503,
            detail="Event queue temporarily unavailable",
        )

    logger.info("Batch created", count=len(events_to_send))

    return {
        "status": "accepted",
        "count": len(events_to_send),
        "event_ids": event_ids,
        "message": f"{len(events_to_send)} events queued for processing",
    }


@router.get("", response_model=EventsListResponse)
async def list_events(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    start_time: Optional[datetime] = Query(None, description="Start time filter"),
    end_time: Optional[datetime] = Query(None, description="End time filter"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum events to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> EventsListResponse:
    """
    List events with optional filters.

    Supports filtering by event type, user ID, and time range.
    Results are paginated.
    """
    try:
        clickhouse = await get_clickhouse_client()
        events = await clickhouse.query_events(
            event_type=event_type,
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )

        return EventsListResponse(
            events=events,
            total=len(events),  # In production, get actual count
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error("Failed to query events", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve events",
        )


@router.get("/{event_id}")
async def get_event(event_id: str) -> Dict[str, Any]:
    """Get a specific event by ID."""
    try:
        clickhouse = await get_clickhouse_client()
        # Query for specific event
        query = f"""
        SELECT * FROM events WHERE id = '{event_id}' LIMIT 1
        """
        result = clickhouse._client.query(query)

        if not result.result_rows:
            raise HTTPException(status_code=404, detail="Event not found")

        row = result.result_rows[0]
        import json

        return {
            "id": str(row[0]),
            "event_type": row[1],
            "user_id": row[2],
            "session_id": row[3],
            "payload": json.loads(row[4]) if row[4] else {},
            "metadata": json.loads(row[5]) if row[5] else {},
            "timestamp": row[6].isoformat() if row[6] else None,
            "processed_at": row[7].isoformat() if row[7] else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get event", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve event")


@router.post("/generate", response_model=Dict[str, Any])
async def generate_events(
    request: GenerateEventsRequest,
) -> Dict[str, Any]:
    """
    Generate sample events for testing.

    Creates realistic events and sends them to Kafka for processing.
    Useful for demos and development.
    """
    generator = EventGenerator(user_count=request.user_count)

    try:
        # Generate events
        events = await generator.generate_events(
            count=request.count,
            event_type=request.event_type,
            delay_ms=request.delay_ms,
        )

        # Send to Kafka
        producer = await get_producer()
        await producer.send_batch(
            topic=settings.kafka_events_topic,
            messages=events,
        )

        logger.info("Generated and sent events", count=request.count)

        return {
            "status": "success",
            "generated": request.count,
            "message": f"Generated and queued {request.count} events",
        }

    except Exception as e:
        logger.error("Failed to generate events", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate events: {str(e)}",
        )
