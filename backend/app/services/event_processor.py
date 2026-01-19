"""Event processing service."""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from prometheus_client import Counter, Histogram

from app.core.logging import get_logger
from app.clickhouse.client import ClickHouseClient

logger = get_logger(__name__)

# Prometheus metrics
EVENTS_PROCESSED = Counter(
    "events_processed_total",
    "Total events processed",
    ["event_type", "status"],
)
PROCESSING_LATENCY = Histogram(
    "event_processing_duration_seconds",
    "Event processing latency",
    ["event_type"],
)
BATCH_PROCESSING_TIME = Histogram(
    "event_batch_processing_duration_seconds",
    "Batch processing time",
)


class EventProcessor:
    """Processes events from Kafka and stores them in ClickHouse."""

    def __init__(self, clickhouse_client: ClickHouseClient):
        self.clickhouse = clickhouse_client
        self._batch: List[Dict[str, Any]] = []
        self._batch_size = 100
        self._batch_timeout = 5.0  # seconds
        self._last_flush = datetime.utcnow()
        self._lock = asyncio.Lock()

    async def process_event(self, event: Dict[str, Any]) -> None:
        """Process a single event."""
        event_type = event.get("event_type", "unknown")

        try:
            with PROCESSING_LATENCY.labels(event_type=event_type).time():
                # Enrich event
                enriched_event = self._enrich_event(event)

                # Add to batch
                async with self._lock:
                    self._batch.append(enriched_event)

                    # Flush if batch is full
                    if len(self._batch) >= self._batch_size:
                        await self._flush_batch()

            EVENTS_PROCESSED.labels(event_type=event_type, status="success").inc()

        except Exception as e:
            EVENTS_PROCESSED.labels(event_type=event_type, status="error").inc()
            logger.error(
                "Failed to process event",
                event_type=event_type,
                error=str(e),
            )
            raise

    async def process_batch(self, events: List[Dict[str, Any]]) -> None:
        """Process a batch of events."""
        if not events:
            return

        try:
            with BATCH_PROCESSING_TIME.time():
                enriched_events = [self._enrich_event(e) for e in events]
                await self.clickhouse.insert_events(enriched_events)

            for event in events:
                event_type = event.get("event_type", "unknown")
                EVENTS_PROCESSED.labels(event_type=event_type, status="success").inc()

            logger.debug("Batch processed", count=len(events))

        except Exception as e:
            for event in events:
                event_type = event.get("event_type", "unknown")
                EVENTS_PROCESSED.labels(event_type=event_type, status="error").inc()

            logger.error("Failed to process batch", error=str(e), count=len(events))
            raise

    def _enrich_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich event with additional metadata."""
        enriched = event.copy()

        # Ensure required fields
        if "timestamp" not in enriched:
            enriched["timestamp"] = datetime.utcnow()
        elif isinstance(enriched["timestamp"], str):
            try:
                enriched["timestamp"] = datetime.fromisoformat(
                    enriched["timestamp"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                enriched["timestamp"] = datetime.utcnow()

        if "processed_at" not in enriched:
            enriched["processed_at"] = datetime.utcnow()
        elif isinstance(enriched["processed_at"], str):
            try:
                enriched["processed_at"] = datetime.fromisoformat(
                    enriched["processed_at"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                enriched["processed_at"] = datetime.utcnow()

        # Normalize event type
        if "event_type" in enriched:
            enriched["event_type"] = str(enriched["event_type"]).lower()

        return enriched

    async def _flush_batch(self) -> None:
        """Flush the current batch to ClickHouse."""
        if not self._batch:
            return

        batch_to_flush = self._batch
        self._batch = []
        self._last_flush = datetime.utcnow()

        try:
            await self.clickhouse.insert_events(batch_to_flush)
            logger.debug("Flushed batch to ClickHouse", count=len(batch_to_flush))
        except Exception as e:
            # Re-add to batch on failure
            self._batch = batch_to_flush + self._batch
            logger.error("Failed to flush batch", error=str(e))
            raise

    async def flush(self) -> None:
        """Force flush any pending events."""
        async with self._lock:
            await self._flush_batch()

    async def start_flush_timer(self) -> None:
        """Start background timer for periodic batch flushing."""
        while True:
            await asyncio.sleep(self._batch_timeout)
            async with self._lock:
                time_since_flush = (datetime.utcnow() - self._last_flush).total_seconds()
                if time_since_flush >= self._batch_timeout and self._batch:
                    await self._flush_batch()
