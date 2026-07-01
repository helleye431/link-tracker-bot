from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, AnyHttpUrl


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="UTF-8")

    bot_token: SecretStr = SecretStr("")
    interservice_transport: str = "http"
    notification_transport: str = "http"

    kafka_bootstrap_servers: str = ""
    kafka_notification_consumer_group: str = ""
    kafka_auto_offset_reset: str = ""
    kafka_enable_auto_commit: bool = False
    kafka_notification_topic: str = ""
    kafka_notification_dlq_topic: str = ""
    kafka_max_processing_retries: int = 0
    schema_registry_url: str = ""

    scrapper_url: AnyHttpUrl = AnyHttpUrl("http://localhost:8080")
    scrapper_grpc_target: str = "scrapper_service:50051"
    metrics_host: str = "0.0.0.0"
    metrics_port: int = 8011

    bot_url: AnyHttpUrl = AnyHttpUrl("http://localhost:8000")
    bot_grpc_host: str = "0.0.0.0"
    bot_grpc_port: int = 50052

    redis_url: str = "redis://redis:6379/0"
    redis_delivered_notifications_ttl_seconds: int = 86400

    timeout_seconds: int = 5
    retry_attempts: int = 5
    retry_backoff_seconds: int = 3
    retry_enable_exponential_backoff: bool = False
    retryable_status_codes: str = "500,400"
    circuit_error_ratio: float = 0.5
    circuit_response_time: int = 5
    circuit_recovery_time: int = 10
    circuit_broken_time: int = 20
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


settings = Settings()
