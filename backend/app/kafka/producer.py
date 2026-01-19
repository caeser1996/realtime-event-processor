"""Kafka producer for event publishing."""

import asyncio
import json
from typing import Any, Dict, Optional

from aiokafka import AIOKafkaProducer
from prometheus_client import Counter, Histogram

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Prometheus metrics
MESSAGES_PRODUCED = Counter(
    "kafka_messages_produced_total",
    "Total number of messages produced to Kafka",
    ["topic"],
)
PRODUCE_LATENCY = Histogram(
    "kafka_produce_duration_seconds",
    "Time spent producing messages to Kafka",
    ["topic"],
)
PRODUCE_ERRORS = Counter(
    "kafka_produce_errors_total",
    "Total number of Kafka produce errors",
    ["topic"],
)


class KafkaProducer:
    """Async Kafka producer with connection management."""

    def __init__(self):
        self._producer: Optional[AIOKafkaProducer] = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the Kafka producer."""
        async with self._lock:
            if self._producer is not None:
                return

            logger.info(
                "Starting Kafka producer",
                bootstrap_servers=settings.kafka_bootstrap_servers,
            )

            self._producer = AIOKafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",
                enable_idempotence=True,
                max_batch_size=16384,
                linger_ms=10,
                compression_type="gzip",
            )

            await self._producer.start()
            logger.info("Kafka producer started successfully")

    async def stop(self) -> None:
        """Stop the Kafka producer."""
        async with self._lock:
            if self._producer is None:
                return

            logger.info("Stopping Kafka producer")
            await self._producer.stop()
            self._producer = None
            logger.info("Kafka producer stopped")

    async def send(
        self,
        topic: str,
        value: Dict[str, Any],
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """Send a message to a Kafka topic."""
        if self._producer is None:
            await self.start()

        kafka_headers = None
        if headers:
            kafka_headers = [(k, v.encode("utf-8")) for k, v in headers.items()]

        try:
            with PRODUCE_LATENCY.labels(topic=topic).time():
                await self._producer.send_and_wait(
                    topic=topic,
                    value=value,
                    key=key,
                    headers=kafka_headers,
                )
            MESSAGES_PRODUCED.labels(topic=topic).inc()
            logger.debug("Message sent to Kafka", topic=topic, key=key)

        except Exception as e:
            PRODUCE_ERRORS.labels(topic=topic).inc()
            logger.error(
                "Failed to send message to Kafka",
                topic=topic,
                error=str(e),
            )
            raise

    async def send_batch(
        self, topic: str, messages: list[Dict[str, Any]]
    ) -> None:
        """Send a batch of messages to a Kafka topic."""
        if self._producer is None:
            await self.start()

        try:
            batch = self._producer.create_batch()
            for msg in messages:
                serialized = json.dumps(msg, default=str).encode("utf-8")
                metadata = batch.append(key=None, value=serialized, timestamp=None)
                if metadata is None:
                    # Batch is full, send it and create a new one
                    await self._producer.send_batch(batch, topic)
                    MESSAGES_PRODUCED.labels(topic=topic).inc(batch.record_count())
                    batch = self._producer.create_batch()
                    batch.append(key=None, value=serialized, timestamp=None)

            # Send remaining messages
            if batch.record_count() > 0:
                await self._producer.send_batch(batch, topic)
                MESSAGES_PRODUCED.labels(topic=topic).inc(batch.record_count())

            logger.debug(
                "Batch sent to Kafka",
                topic=topic,
                count=len(messages),
            )

        except Exception as e:
            PRODUCE_ERRORS.labels(topic=topic).inc(len(messages))
            logger.error(
                "Failed to send batch to Kafka",
                topic=topic,
                error=str(e),
            )
            raise

    @property
    def is_connected(self) -> bool:
        """Check if producer is connected."""
        return self._producer is not None


# Global producer instance
_producer: Optional[KafkaProducer] = None


async def get_producer() -> KafkaProducer:
    """Get the global Kafka producer instance."""
    global _producer
    if _producer is None:
        _producer = KafkaProducer()
        await _producer.start()
    return _producer


async def close_producer() -> None:
    """Close the global Kafka producer."""
    global _producer
    if _producer is not None:
        await _producer.stop()
        _producer = None
