from scrapper_service.application.ports.notification_client_port import (
    NotificationClientPort,
)
from scrapper_service.infrastructure.clients.grpc_bot_client import GrpcBotClient
from scrapper_service.infrastructure.clients.http_bot_client import HttpBotClient
from scrapper_service.infrastructure.clients.kafka_notification_client import (
    KafkaNotificationClient,
)
from scrapper_service.infrastructure.clients.utils.resilient_http_client import (
    ResilientHttpClient,
)


def build_notification_client(
    notification_transport: str,
    bot_grpc_target: str,
    bot_http_url: str,
    kafka_bootstrap_servers,
    kafka_topic,
    schema_registry_url,
    timeout_seconds: int,
    retry_attempts: int,
    retry_backoff_seconds: int,
    retry_enable_exponential_backoff: bool,
    retryable_status_codes: list[int],
    circuit_error_ratio: float,
    circuit_response_time: float,
    circuit_recovery_time: float,
    circuit_broken_time: float,
) -> NotificationClientPort:

    match notification_transport:
        case "grpc":
            return GrpcBotClient(bot_grpc_target)
        case "http":
            resilient_client = ResilientHttpClient(
                timeout_seconds=timeout_seconds,
                retry_attempts=retry_attempts,
                retry_backoff_seconds=retry_backoff_seconds,
                retryable_status_codes=retryable_status_codes,
                circuit_error_ratio=circuit_error_ratio,
                circuit_response_time=circuit_response_time,
                circuit_broken_time=circuit_broken_time,
                circuit_recovery_time=circuit_recovery_time,
                retry_enable_exponential_backoff=retry_enable_exponential_backoff,
            )
            return HttpBotClient(bot_http_url, client=resilient_client)
        case "kafka":
            return KafkaNotificationClient(
                bootstrap_servers=kafka_bootstrap_servers,
                topic=kafka_topic,
                schema_registry_url=schema_registry_url,
            )
        case _:
            raise ValueError(f"Неизвестный тип транспорта: {notification_transport}")
