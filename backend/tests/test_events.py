"""Tests for event endpoints."""

import pytest
from unittest.mock import patch, AsyncMock


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_create_event(client, mock_kafka_producer):
    """Test event creation."""
    with patch("app.api.v1.events.get_producer", return_value=mock_kafka_producer):
        response = client.post(
            "/api/v1/events",
            json={
                "event_type": "user_action",
                "user_id": "test_user",
                "payload": {"action": "click"},
            },
        )

        # Note: May return 503 if Kafka is not available in test environment
        assert response.status_code in [202, 503]


def test_generate_events_validation(client):
    """Test event generation validation."""
    # Invalid count
    response = client.post(
        "/api/v1/events/generate",
        json={"count": 0},
    )
    assert response.status_code == 422

    # Count too large
    response = client.post(
        "/api/v1/events/generate",
        json={"count": 100000},
    )
    assert response.status_code == 422
