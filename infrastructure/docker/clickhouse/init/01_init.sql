-- Initialize ClickHouse database for event processing

-- Create events database
CREATE DATABASE IF NOT EXISTS events;

-- Use events database
USE events;

-- Main events table with optimal settings for time-series analytics
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
SETTINGS index_granularity = 8192;

-- Hourly aggregation table for faster queries
CREATE TABLE IF NOT EXISTS events_hourly (
    hour DateTime,
    event_type LowCardinality(String),
    event_count UInt64,
    unique_users UInt64,
    unique_sessions UInt64
) ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(hour)
ORDER BY (hour, event_type)
TTL hour + INTERVAL 365 DAY;

-- Materialized view for automatic hourly aggregation
CREATE MATERIALIZED VIEW IF NOT EXISTS events_realtime_mv
TO events_hourly
AS SELECT
    toStartOfHour(timestamp) AS hour,
    event_type,
    count() AS event_count,
    uniqExact(user_id) AS unique_users,
    uniqExact(session_id) AS unique_sessions
FROM events
GROUP BY hour, event_type;

-- User sessions table for session analytics
CREATE TABLE IF NOT EXISTS user_sessions (
    session_id String,
    user_id Nullable(String),
    first_event DateTime64(3),
    last_event DateTime64(3),
    event_count UInt32,
    pages_visited Array(String),
    date Date DEFAULT toDate(first_event)
) ENGINE = ReplacingMergeTree(last_event)
PARTITION BY toYYYYMM(date)
ORDER BY (session_id)
TTL date + INTERVAL 30 DAY;

-- Daily summary table for historical analysis
CREATE TABLE IF NOT EXISTS events_daily (
    date Date,
    event_type LowCardinality(String),
    event_count UInt64,
    unique_users UInt64,
    unique_sessions UInt64,
    avg_events_per_user Float64
) ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, event_type)
TTL date + INTERVAL 730 DAY;

-- Materialized view for daily aggregation
CREATE MATERIALIZED VIEW IF NOT EXISTS events_daily_mv
TO events_daily
AS SELECT
    toDate(timestamp) AS date,
    event_type,
    count() AS event_count,
    uniqExact(user_id) AS unique_users,
    uniqExact(session_id) AS unique_sessions,
    count() / uniqExact(user_id) AS avg_events_per_user
FROM events
GROUP BY date, event_type;
