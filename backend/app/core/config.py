"""Application configuration using Pydantic settings."""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Real-time Event Processor"
    app_version: str = "1.0.0"
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)

    # Kafka
    kafka_bootstrap_servers: str = Field(default="kafka:29092")
    kafka_events_topic: str = Field(default="events")
    kafka_processed_topic: str = Field(default="events-processed")
    kafka_consumer_group: str = Field(default="event-processor")
    kafka_auto_offset_reset: str = Field(default="earliest")
    kafka_enable_auto_commit: bool = Field(default=True)
    kafka_max_poll_records: int = Field(default=500)
    kafka_session_timeout_ms: int = Field(default=30000)

    # ClickHouse
    clickhouse_host: str = Field(default="clickhouse")
    clickhouse_port: int = Field(default=8123)
    clickhouse_database: str = Field(default="events")
    clickhouse_user: str = Field(default="default")
    clickhouse_password: str = Field(default="clickhouse")

    # Redis
    redis_url: str = Field(default="redis://redis:6379")
    redis_cache_ttl: int = Field(default=300)  # 5 minutes

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"]
    )

    # Rate limiting
    rate_limit_requests: int = Field(default=100)
    rate_limit_window: int = Field(default=60)  # seconds

    @property
    def kafka_bootstrap_servers_list(self) -> List[str]:
        """Return Kafka bootstrap servers as a list."""
        return self.kafka_bootstrap_servers.split(",")

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
