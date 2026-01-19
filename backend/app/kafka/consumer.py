"""Kafka consumer for event processing."""

import asyncio
import json
import signal
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from aiokafka import AIOKafkaConsumer
from prometheus_client import Counter, Gauge, Histogram

from app.core.config import settings
from app.core.logging import get_logger
from app.clickhouse.client import get_clickhouse_client
from app.services.event_processor import EventProcessor

logger = get_logger(__name__)

# Prometheus metrics
MESSAGES_CONSUMED = Counter(
    "kafka_messages_consumed_total",
    "Total number of messages consumed from Kafka",
    ["topic", "consumer_group"],
)
CONSUME_LATENCY = Histogram(
    "kafka_consume_duration_seconds",
    "Time spent consuming and processing messages",
    ["topic"],
)
CONSUMER_LAG = Gauge(
    "kafka_consumer_lag",
    "Current consumer lag",
    ["topic", "partition"],
)
CONSUME_ERRORS = Counter(
    "kafka_consume_errors_total",
    "Total number of Kafka consume errors",
    ["topic"],
)
BATCH_SIZE = Histogram(
    "kafka_batch_size",
    "Size of consumed message batches",
    ["topic"],
)


class KafkaConsumer:
    """Async Kafka consumer with batch processing."""

    def __init__(
        self,
        topics: list[str],
        group_id: str,
        process_callback: Optional[Callable] = None,
    ):
        self.topics = topics
        self.group_id = group_id
        self.process_callback = process_callback
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._running = False
        self._processor: Optional[EventProcessor] = None

    async def start(self) -> None:
        """Start the Kafka consumer."""
        logger.info(
            "Starting Kafka consumer",
            topics=self.topics,
            group_id=self.group_id,
            bootstrap_servers=settings.kafka_bootstrap_servers,
        )

        self._consumer = AIOKafkaConsumer(
            *self.topics,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset=settings.kafka_auto_offset_reset,
            enable_auto_commit=settings.kafka_enable_auto_commit,
            max_poll_records=settings.kafka_max_poll_records,
            session_timeout_ms=settings.kafka_session_timeout_ms,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )

        await self._consumer.start()
        self._running = True

        # Initialize event processor
        clickhouse = await get_clickhouse_client()
        self._processor = EventProcessor(clickhouse)

        logger.info("Kafka consumer started successfully")

    async def stop(self) -> None:
        """Stop the Kafka consumer."""
        logger.info("Stopping Kafka consumer")
        self._running = False

        if self._consumer:
            await self._consumer.stop()
            self._consumer = None

        logger.info("Kafka consumer stopped")

    async def consume(self) -> None:
        """Main consumption loop."""
        if not self._consumer:
            await self.start()

        logger.info("Starting consumption loop")

        try:
            async for message in self._consumer:
                if not self._running:
                    break

                try:
                    with CONSUME_LATENCY.labels(topic=message.topic).time():
                        await self._process_message(message)

                    MESSAGES_CONSUMED.labels(
                        topic=message.topic,
                        consumer_group=self.group_id,
                    ).inc()

                except Exception as e:
                    CONSUME_ERRORS.labels(topic=message.topic).inc()
                    logger.error(
                        "Error processing message",
                        topic=message.topic,
                        partition=message.partition,
                        offset=message.offset,
                        error=str(e),
                    )

        except Exception as e:
            logger.error("Consumer loop error", error=str(e))
            raise

    async def consume_batch(self, batch_size: int = 100, timeout_ms: int = 1000) -> None:
        """Consume messages in batches for better throughput."""
        if not self._consumer:
            await self.start()

        logger.info("Starting batch consumption loop", batch_size=batch_size)

        while self._running:
            try:
                # Get batch of messages
                result = await self._consumer.getmany(
                    timeout_ms=timeout_ms,
                    max_records=batch_size,
                )

                for topic_partition, messages in result.items():
                    if not messages:
                        continue

                    BATCH_SIZE.labels(topic=topic_partition.topic).observe(len(messages))

                    # Process batch
                    events = []
                    for msg in messages:
                        try:
                            events.append(msg.value)
                        except Exception as e:
                            logger.error("Error parsing message", error=str(e))
                            CONSUME_ERRORS.labels(topic=topic_partition.topic).inc()

                    if events and self._processor:
                        with CONSUME_LATENCY.labels(topic=topic_partition.topic).time():
                            await self._processor.process_batch(events)

                    MESSAGES_CONSUMED.labels(
                        topic=topic_partition.topic,
                        consumer_group=self.group_id,
                    ).inc(len(messages))

                    # Update lag metric
                    end_offsets = await self._consumer.end_offsets([topic_partition])
                    lag = end_offsets[topic_partition] - messages[-1].offset - 1
                    CONSUMER_LAG.labels(
                        topic=topic_partition.topic,
                        partition=topic_partition.partition,
                    ).set(lag)

            except Exception as e:
                logger.error("Batch consumption error", error=str(e))
                await asyncio.sleep(1)

    async def _process_message(self, message: Any) -> None:
        """Process a single message."""
        event_data = message.value

        # Add processing metadata
        event_data["processed_at"] = datetime.utcnow().isoformat()
        event_data["kafka_topic"] = message.topic
        event_data["kafka_partition"] = message.partition
        event_data["kafka_offset"] = message.offset

        # Use callback if provided
        if self.process_callback:
            await self.process_callback(event_data)
        elif self._processor:
            await self._processor.process_event(event_data)

        logger.debug(
            "Message processed",
            topic=message.topic,
            partition=message.partition,
            offset=message.offset,
        )


async def run_consumer():
    """Run the consumer as a standalone process."""
    logger.info("Initializing event consumer process")

    consumer = KafkaConsumer(
        topics=[settings.kafka_events_topic],
        group_id=settings.kafka_consumer_group,
    )

    # Handle shutdown signals
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def signal_handler():
        logger.info("Received shutdown signal")
        stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await consumer.start()

        # Run consumer until shutdown
        consumer_task = asyncio.create_task(consumer.consume_batch())

        await stop_event.wait()

        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

    finally:
        await consumer.stop()

    logger.info("Consumer shutdown complete")


if __name__ == "__main__":
    asyncio.run(run_consumer())
