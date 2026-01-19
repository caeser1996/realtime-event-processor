"""Seed database with sample data."""

import asyncio

from app.core.logging import setup_logging, get_logger
from app.clickhouse.client import get_clickhouse_client, close_clickhouse_client
from app.services.event_generator import EventGenerator

setup_logging()
logger = get_logger(__name__)


async def seed_database(event_count: int = 10000) -> None:
    """Seed the database with sample events."""
    logger.info("Starting database seeding", event_count=event_count)

    try:
        # Initialize ClickHouse client
        clickhouse = await get_clickhouse_client()

        # Generate events
        generator = EventGenerator(user_count=100)
        events = generator.generate_events_sync(count=event_count)

        # Insert in batches
        batch_size = 1000
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            await clickhouse.insert_events(batch)
            logger.info(f"Inserted batch {i // batch_size + 1}", count=len(batch))

        logger.info("Database seeding complete", total=event_count)

    except Exception as e:
        logger.error("Failed to seed database", error=str(e))
        raise
    finally:
        await close_clickhouse_client()


if __name__ == "__main__":
    asyncio.run(seed_database())
