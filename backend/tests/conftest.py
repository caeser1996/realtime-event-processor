"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer."""
    producer = AsyncMock()
    producer.send = AsyncMock()
    producer.send_batch = AsyncMock()
    producer.is_connected = True
    return producer


@pytest.fixture
def mock_clickhouse_client():
    """Mock ClickHouse client."""
    client = AsyncMock()
    client.insert_events = AsyncMock()
    client.query_events = AsyncMock(return_value=[])
    client.get_event_stats = AsyncMock(return_value={
        "total_events": 0,
        "unique_users": 0,
        "unique_sessions": 0,
        "events_by_type": {},
        "time_range": {"start": None, "end": None},
    })
    client.get_realtime_metrics = AsyncMock(return_value={
        "timestamp": "2024-01-01T00:00:00",
        "events_last_minute": 0,
        "events_last_hour": 0,
        "active_users": 0,
        "active_sessions": 0,
        "events_per_second": 0.0,
        "error_count": 0,
        "top_event_types": [],
    })
    client.is_connected = True
    return client
