"""ClickHouse client for analytics storage and queries."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import clickhouse_connect
from clickhouse_connect.driver.client import Client
from prometheus_client import Counter, Histogram

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Prometheus metrics
QUERIES_EXECUTED = Counter(
    "clickhouse_queries_total",
    "Total ClickHouse queries executed",
    ["query_type"],
)
QUERY_LATENCY = Histogram(
    "clickhouse_query_duration_seconds",
    "ClickHouse query latency",
    ["query_type"],
)
QUERY_ERRORS = Counter(
    "clickhouse_query_errors_total",
    "Total ClickHouse query errors",
    ["query_type"],
)
ROWS_INSERTED = Counter(
    "clickhouse_rows_inserted_total",
    "Total rows inserted into ClickHouse",
    ["table"],
)


class ClickHouseClient:
    """ClickHouse client with connection pooling and query helpers."""

    def __init__(self):
        self._client: Optional[Client] = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """Establish connection to ClickHouse."""
        async with self._lock:
            if self._client is not None:
                return

            logger.info(
                "Connecting to ClickHouse",
                host=settings.clickhouse_host,
                port=settings.clickhouse_port,
                database=settings.clickhouse_database,
            )

            self._client = clickhouse_connect.get_client(
                host=settings.clickhouse_host,
                port=settings.clickhouse_port,
                database=settings.clickhouse_database,
                username=settings.clickhouse_user,
                password=settings.clickhouse_password,
            )

            # Initialize tables
            await self._initialize_tables()

            logger.info("Connected to ClickHouse successfully")

    async def close(self) -> None:
        """Close ClickHouse connection."""
        async with self._lock:
            if self._client:
                self._client.close()
                self._client = None
                logger.info("ClickHouse connection closed")

    async def _initialize_tables(self) -> None:
        """Create required tables if they don't exist."""
        create_events_table = """
        CREATE TABLE IF NOT EXISTS events (
            id UUID DEFAULT generateUUIDv4(),
            event_type LowCardinality(String),
            user_id Nullable(String),
            session_id Nullable(String),
            payload String,
            metadata String,
            timestamp DateTime64(3) DEFAULT now64(3),
            processed_at DateTime64(3) DEFAULT now64(3),
            source_ip Nullable(String),
            user_agent Nullable(String),
            date Date DEFAULT toDate(timestamp)
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(date)
        ORDER BY (event_type, timestamp, id)
        TTL date + INTERVAL 90 DAY
        SETTINGS index_granularity = 8192
        """

        create_events_hourly_table = """
        CREATE TABLE IF NOT EXISTS events_hourly (
            hour DateTime,
            event_type LowCardinality(String),
            event_count UInt64,
            unique_users UInt64,
            unique_sessions UInt64
        ) ENGINE = SummingMergeTree()
        PARTITION BY toYYYYMM(hour)
        ORDER BY (hour, event_type)
        TTL hour + INTERVAL 365 DAY
        """

        create_events_realtime_view = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS events_realtime_mv
        TO events_hourly
        AS SELECT
            toStartOfHour(timestamp) AS hour,
            event_type,
            count() AS event_count,
            uniqExact(user_id) AS unique_users,
            uniqExact(session_id) AS unique_sessions
        FROM events
        GROUP BY hour, event_type
        """

        try:
            self._client.command(create_events_table)
            self._client.command(create_events_hourly_table)
            self._client.command(create_events_realtime_view)
            logger.info("ClickHouse tables initialized")
        except Exception as e:
            logger.error("Failed to initialize tables", error=str(e))
            raise

    async def insert_event(self, event: Dict[str, Any]) -> None:
        """Insert a single event into ClickHouse."""
        await self.insert_events([event])

    async def insert_events(self, events: List[Dict[str, Any]]) -> None:
        """Insert multiple events into ClickHouse."""
        if not self._client:
            await self.connect()

        try:
            import json

            data = []
            for event in events:
                data.append({
                    "id": event.get("id"),
                    "event_type": event.get("event_type", "unknown"),
                    "user_id": event.get("user_id"),
                    "session_id": event.get("session_id"),
                    "payload": json.dumps(event.get("payload", {})),
                    "metadata": json.dumps(event.get("metadata", {})),
                    "timestamp": event.get("timestamp", datetime.utcnow()),
                    "processed_at": event.get("processed_at", datetime.utcnow()),
                    "source_ip": event.get("source_ip"),
                    "user_agent": event.get("user_agent"),
                })

            with QUERY_LATENCY.labels(query_type="insert").time():
                self._client.insert(
                    "events",
                    data,
                    column_names=[
                        "id", "event_type", "user_id", "session_id",
                        "payload", "metadata", "timestamp", "processed_at",
                        "source_ip", "user_agent"
                    ],
                )

            ROWS_INSERTED.labels(table="events").inc(len(events))
            QUERIES_EXECUTED.labels(query_type="insert").inc()

            logger.debug("Inserted events into ClickHouse", count=len(events))

        except Exception as e:
            QUERY_ERRORS.labels(query_type="insert").inc()
            logger.error("Failed to insert events", error=str(e))
            raise

    async def query_events(
        self,
        event_type: Optional[str] = None,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Query events with filters."""
        if not self._client:
            await self.connect()

        conditions = ["1=1"]
        params = {}

        if event_type:
            conditions.append("event_type = {event_type:String}")
            params["event_type"] = event_type

        if user_id:
            conditions.append("user_id = {user_id:String}")
            params["user_id"] = user_id

        if start_time:
            conditions.append("timestamp >= {start_time:DateTime64(3)}")
            params["start_time"] = start_time

        if end_time:
            conditions.append("timestamp <= {end_time:DateTime64(3)}")
            params["end_time"] = end_time

        query = f"""
        SELECT
            id,
            event_type,
            user_id,
            session_id,
            payload,
            metadata,
            timestamp,
            processed_at,
            source_ip,
            user_agent
        FROM events
        WHERE {' AND '.join(conditions)}
        ORDER BY timestamp DESC
        LIMIT {limit} OFFSET {offset}
        """

        try:
            with QUERY_LATENCY.labels(query_type="select").time():
                result = self._client.query(query, parameters=params)

            QUERIES_EXECUTED.labels(query_type="select").inc()

            import json
            events = []
            for row in result.result_rows:
                events.append({
                    "id": str(row[0]),
                    "event_type": row[1],
                    "user_id": row[2],
                    "session_id": row[3],
                    "payload": json.loads(row[4]) if row[4] else {},
                    "metadata": json.loads(row[5]) if row[5] else {},
                    "timestamp": row[6].isoformat() if row[6] else None,
                    "processed_at": row[7].isoformat() if row[7] else None,
                    "source_ip": row[8],
                    "user_agent": row[9],
                })

            return events

        except Exception as e:
            QUERY_ERRORS.labels(query_type="select").inc()
            logger.error("Failed to query events", error=str(e))
            raise

    async def get_event_stats(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get event statistics for a time range."""
        if not self._client:
            await self.connect()

        if not start_time:
            start_time = datetime.utcnow() - timedelta(hours=24)
        if not end_time:
            end_time = datetime.utcnow()

        query = """
        SELECT
            count() AS total_events,
            uniqExact(user_id) AS unique_users,
            uniqExact(session_id) AS unique_sessions,
            min(timestamp) AS min_time,
            max(timestamp) AS max_time
        FROM events
        WHERE timestamp >= {start_time:DateTime64(3)}
          AND timestamp <= {end_time:DateTime64(3)}
        """

        type_query = """
        SELECT
            event_type,
            count() AS count
        FROM events
        WHERE timestamp >= {start_time:DateTime64(3)}
          AND timestamp <= {end_time:DateTime64(3)}
        GROUP BY event_type
        ORDER BY count DESC
        """

        try:
            with QUERY_LATENCY.labels(query_type="stats").time():
                result = self._client.query(
                    query,
                    parameters={"start_time": start_time, "end_time": end_time},
                )
                type_result = self._client.query(
                    type_query,
                    parameters={"start_time": start_time, "end_time": end_time},
                )

            QUERIES_EXECUTED.labels(query_type="stats").inc()

            row = result.result_rows[0] if result.result_rows else (0, 0, 0, None, None)
            events_by_type = {r[0]: r[1] for r in type_result.result_rows}

            return {
                "total_events": row[0],
                "unique_users": row[1],
                "unique_sessions": row[2],
                "events_by_type": events_by_type,
                "time_range": {
                    "start": row[3].isoformat() if row[3] else None,
                    "end": row[4].isoformat() if row[4] else None,
                },
            }

        except Exception as e:
            QUERY_ERRORS.labels(query_type="stats").inc()
            logger.error("Failed to get event stats", error=str(e))
            raise

    async def get_realtime_metrics(self) -> Dict[str, Any]:
        """Get real-time metrics for the dashboard."""
        if not self._client:
            await self.connect()

        now = datetime.utcnow()
        one_minute_ago = now - timedelta(minutes=1)
        one_hour_ago = now - timedelta(hours=1)
        five_minutes_ago = now - timedelta(minutes=5)

        queries = {
            "last_minute": f"""
                SELECT count() FROM events
                WHERE timestamp >= '{one_minute_ago.isoformat()}'
            """,
            "last_hour": f"""
                SELECT count() FROM events
                WHERE timestamp >= '{one_hour_ago.isoformat()}'
            """,
            "active_users": f"""
                SELECT uniqExact(user_id) FROM events
                WHERE timestamp >= '{five_minutes_ago.isoformat()}'
            """,
            "active_sessions": f"""
                SELECT uniqExact(session_id) FROM events
                WHERE timestamp >= '{five_minutes_ago.isoformat()}'
            """,
            "error_count": f"""
                SELECT count() FROM events
                WHERE timestamp >= '{one_hour_ago.isoformat()}'
                AND event_type = 'error'
            """,
            "top_types": f"""
                SELECT event_type, count() as cnt FROM events
                WHERE timestamp >= '{one_hour_ago.isoformat()}'
                GROUP BY event_type
                ORDER BY cnt DESC
                LIMIT 5
            """,
        }

        try:
            with QUERY_LATENCY.labels(query_type="realtime").time():
                results = {}
                for name, query in queries.items():
                    result = self._client.query(query)
                    results[name] = result.result_rows

            QUERIES_EXECUTED.labels(query_type="realtime").inc()

            last_minute = results["last_minute"][0][0] if results["last_minute"] else 0
            last_hour = results["last_hour"][0][0] if results["last_hour"] else 0

            return {
                "timestamp": now.isoformat(),
                "events_last_minute": last_minute,
                "events_last_hour": last_hour,
                "active_users": results["active_users"][0][0] if results["active_users"] else 0,
                "active_sessions": results["active_sessions"][0][0] if results["active_sessions"] else 0,
                "events_per_second": round(last_minute / 60, 2),
                "error_count": results["error_count"][0][0] if results["error_count"] else 0,
                "top_event_types": [
                    {"type": r[0], "count": r[1]}
                    for r in results["top_types"]
                ],
            }

        except Exception as e:
            QUERY_ERRORS.labels(query_type="realtime").inc()
            logger.error("Failed to get realtime metrics", error=str(e))
            raise

    async def get_time_series(
        self,
        interval: str = "1h",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get time series data for charts."""
        if not self._client:
            await self.connect()

        if not start_time:
            start_time = datetime.utcnow() - timedelta(hours=24)
        if not end_time:
            end_time = datetime.utcnow()

        interval_map = {
            "1m": "toStartOfMinute",
            "5m": "toStartOfFiveMinutes",
            "15m": "toStartOfFifteenMinutes",
            "1h": "toStartOfHour",
            "1d": "toStartOfDay",
        }

        interval_func = interval_map.get(interval, "toStartOfHour")

        query = f"""
        SELECT
            {interval_func}(timestamp) AS time_bucket,
            count() AS event_count,
            uniqExact(user_id) AS unique_users
        FROM events
        WHERE timestamp >= {{start_time:DateTime64(3)}}
          AND timestamp <= {{end_time:DateTime64(3)}}
        GROUP BY time_bucket
        ORDER BY time_bucket ASC
        """

        try:
            with QUERY_LATENCY.labels(query_type="timeseries").time():
                result = self._client.query(
                    query,
                    parameters={"start_time": start_time, "end_time": end_time},
                )

            QUERIES_EXECUTED.labels(query_type="timeseries").inc()

            return [
                {
                    "timestamp": row[0].isoformat(),
                    "event_count": row[1],
                    "unique_users": row[2],
                }
                for row in result.result_rows
            ]

        except Exception as e:
            QUERY_ERRORS.labels(query_type="timeseries").inc()
            logger.error("Failed to get time series", error=str(e))
            raise

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._client is not None


# Global client instance
_client: Optional[ClickHouseClient] = None


async def get_clickhouse_client() -> ClickHouseClient:
    """Get the global ClickHouse client instance."""
    global _client
    if _client is None:
        _client = ClickHouseClient()
        await _client.connect()
    return _client


async def close_clickhouse_client() -> None:
    """Close the global ClickHouse client."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None
