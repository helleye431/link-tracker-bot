from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    scrapper_http_url: AnyHttpUrl = AnyHttpUrl("http://localhost:8080")
    bot_http_url: AnyHttpUrl = AnyHttpUrl("http://localhost:8000")

    scrapper_grpc_host: str = "0.0.0.0"
    scrapper_grpc_port: int = 50051
    bot_grpc_target: str = "bot:50052"

    github_base_url: AnyHttpUrl = AnyHttpUrl("https://api.github.com")
    stackoverflow_base_url: AnyHttpUrl = AnyHttpUrl("https://api.stackexchange.com/2.3")

    scheduler_interval_seconds: int = 60
    scheduler_batch_size: int = 1
    scheduler_workers_count: int = 2
    interservice_transport: str = "http"
    notification_transport: str = "http"

    transactional_outbox_mode: bool = False
    outbox_processing_delay: int = 1

    kafka_bootstrap_servers: str = "localhost:29092,localhost:29093,localhost:29094"
    kafka_notification_topic: str = "notifications"
    schema_registry_url: str = ""

    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_pass: str = "postgres"
    db_name: str = "links_db"
    access_type: str = "sql"

    enable_cache: bool = False
    valkey_addresses: str = ""
    valkey_enable_client_cache: bool = False
    valkey_cache_ttl: int = 50
    valkey_client_cache_ttl: int = 10
    valkey_client_cache_maxsize: int = 10_000

    timeout_seconds: int = 5
    retry_attempts: int = 5
    retry_backoff_seconds: int = 3
    retry_enable_exponential_backoff: bool = False
    retryable_status_codes: str = "500,400"
    circuit_error_ratio: float = 0.5
    circuit_response_time: float = 5
    circuit_recovery_time: float = 10
    circuit_broken_time: float = 20
    request_limit: int = 5
    request_limit_period: Literal[
        "second",
        "minute",
        "hour",
        "day",
        "month",
        "year",
    ] = "second"

    @property
    def retryable_status_codes_list(self):
        return [int(code) for code in self.retryable_status_codes.split(",")]

    @property
    def valkey_addresses_list(self) -> list[tuple[str, int]]:
        return [
            (link.split(":")[0], int(link.split(":")[1]))
            for link in self.valkey_addresses.strip().split(",")
        ]

    @property
    def database_url_asyncpg(self) -> str:
        return (
            f"postgresql+asyncpg://"
            f"{self.db_user}:{self.db_pass}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def database_url_asyncpg_driver(self) -> str:
        return (
            f"postgresql://"
            f"{self.db_user}:{self.db_pass}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def database_url_psycopg(self) -> str:
        return (
            f"postgresql+psycopg://"
            f"{self.db_user}:{self.db_pass}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )
