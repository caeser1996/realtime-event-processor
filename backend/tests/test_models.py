"""Tests for Pydantic models."""

import pytest
from uuid import UUID
from datetime import datetime

from app.models.events import Event, EventCreate, EventType, GenerateEventsRequest


def test_event_create_model():
    """Test EventCreate model validation."""
    event = EventCreate(
        event_type=EventType.USER_ACTION,
        user_id="user123",
        payload={"action": "click"},
    )

    assert event.event_type == EventType.USER_ACTION
    assert event.user_id == "user123"
    assert event.payload == {"action": "click"}
    assert event.metadata == {}


def test_event_model_defaults():
    """Test Event model default values."""
    event = Event(event_type=EventType.PAGE_VIEW)

    assert isinstance(event.id, UUID)
    assert isinstance(event.timestamp, datetime)
    assert event.payload == {}
    assert event.metadata == {}


def test_generate_events_request_validation():
    """Test GenerateEventsRequest validation."""
    # Valid request
    request = GenerateEventsRequest(count=100, user_count=10)
    assert request.count == 100
    assert request.user_count == 10

    # Invalid count (too low)
    with pytest.raises(ValueError):
        GenerateEventsRequest(count=0)

    # Invalid count (too high)
    with pytest.raises(ValueError):
        GenerateEventsRequest(count=100000)


def test_event_types():
    """Test all event types are valid."""
    valid_types = [
        EventType.USER_ACTION,
        EventType.PAGE_VIEW,
        EventType.CLICK,
        EventType.FORM_SUBMIT,
        EventType.PURCHASE,
        EventType.ERROR,
        EventType.CUSTOM,
    ]

    for event_type in valid_types:
        event = EventCreate(event_type=event_type)
        assert event.event_type == event_type
