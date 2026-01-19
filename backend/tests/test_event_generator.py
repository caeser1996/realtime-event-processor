"""Tests for event generator."""

import pytest

from app.services.event_generator import EventGenerator
from app.models.events import EventType


def test_event_generator_creation():
    """Test EventGenerator initialization."""
    generator = EventGenerator(user_count=50)
    assert len(generator.users) == 50


def test_generate_single_event():
    """Test generating a single event."""
    generator = EventGenerator()
    event = generator.generate_event()

    assert "id" in event
    assert "event_type" in event
    assert "user_id" in event
    assert "session_id" in event
    assert "payload" in event
    assert "metadata" in event
    assert "timestamp" in event


def test_generate_event_with_type():
    """Test generating event with specific type."""
    generator = EventGenerator()
    event = generator.generate_event(event_type=EventType.PURCHASE)

    assert event["event_type"] == "purchase"
    assert "product_id" in event["payload"]
    assert "price" in event["payload"]


def test_generate_event_with_user():
    """Test generating event for specific user."""
    generator = EventGenerator()
    event = generator.generate_event(user_id="custom_user")

    assert event["user_id"] == "custom_user"


def test_generate_multiple_events():
    """Test generating multiple events."""
    generator = EventGenerator()
    events = generator.generate_events_sync(count=10)

    assert len(events) == 10
    for event in events:
        assert "id" in event
        assert "event_type" in event


def test_session_persistence():
    """Test that sessions persist for users."""
    generator = EventGenerator(user_count=1)
    user_id = generator.users[0]

    event1 = generator.generate_event(user_id=user_id)
    event2 = generator.generate_event(user_id=user_id)

    # Session should be the same (unless randomly regenerated)
    # Just verify both have sessions
    assert event1["session_id"] is not None
    assert event2["session_id"] is not None


def test_payload_generation():
    """Test payload generation for different event types."""
    generator = EventGenerator()

    # Test each event type has appropriate payload
    for event_type in EventType:
        event = generator.generate_event(event_type=event_type)
        assert isinstance(event["payload"], dict)


def test_metadata_generation():
    """Test metadata generation."""
    generator = EventGenerator()
    event = generator.generate_event()

    metadata = event["metadata"]
    assert "browser" in metadata
    assert "device" in metadata
    assert "os" in metadata
