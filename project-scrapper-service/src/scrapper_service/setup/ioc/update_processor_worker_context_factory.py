from collections.abc import Awaitable, Callable
from scrapper_service.application.common.contexts.update_processor_worker_context import (
    UpdateProcessorWorkerContext,
)
from scrapper_service.application.ports.notification_client_port import (
    NotificationClientPort,
)
from scrapper_service.application.services.link_update_fetcher_service import (
    LinkUpdateFetcherService,
)
from scrapper_service.application.services.notification_service import (
    NotificationService,
)
from scrapper_service.infrastructure.clients.github_client import GithubClient
from scrapper_service.infrastructure.clients.stackoverflow_client import (
    StackoverflowClient,
)
from scrapper_service.setup.ioc.repository_builder import (
    build_repository,
)
from scrapper_service.setup.ioc.notification_client_builder import (
    build_notification_client,
)


async def build_update_processor_worker_context(
    access_type: str,
    orm_url: str,
    raw_sql_url: str,
    github_base_url: str,
    stackoverflow_base_url: str,
    interservice_transport: str,
    bot_grpc_target: str,
    bot_http_url: str,
    kafka_bootstrap_servers: str,
    kafka_notification_topic: str,
    schema_registry_url: str,
    timeout_seconds: int,
    retry_attempts: int,
    retry_backoff_seconds: int,
    retry_enable_exponential_backoff: bool,
    retryable_status_codes: list[int],
    circuit_error_ratio: float,
    circuit_response_time: float,
    circuit_recovery_time: float,
    circuit_broken_time: float,
) -> UpdateProcessorWorkerContext:
    repository = await build_repository(
        access_type=access_type,
        orm_url=orm_url,
        raw_sql_url=raw_sql_url,
    )

    github_client = GithubClient(github_base_url)
    stackoverflow_client = StackoverflowClient(stackoverflow_base_url)
    bot_client = build_notification_client(
        notification_transport=interservice_transport,
        bot_grpc_target=bot_grpc_target,
        bot_http_url=bot_http_url,
        kafka_bootstrap_servers=kafka_bootstrap_servers,
        kafka_topic=kafka_notification_topic,
        schema_registry_url=schema_registry_url,
        timeout_seconds=timeout_seconds,
        retry_attempts=retry_attempts,
        retry_backoff_seconds=retry_backoff_seconds,
        retry_enable_exponential_backoff=retry_enable_exponential_backoff,
        retryable_status_codes=retryable_status_codes,
        circuit_error_ratio=circuit_error_ratio,
        circuit_response_time=circuit_response_time,
        circuit_recovery_time=circuit_recovery_time,
        circuit_broken_time=circuit_broken_time,
    )

    notification_clients: list[NotificationClientPort] = []
    notification_clients.append(bot_client)

    if interservice_transport != "kafka":
        fallback_client = build_notification_client(
            notification_transport="kafka",
            bot_grpc_target=bot_grpc_target,
            bot_http_url=bot_http_url,
            kafka_bootstrap_servers=kafka_bootstrap_servers,
            kafka_topic=kafka_notification_topic,
            schema_registry_url=schema_registry_url,
            timeout_seconds=timeout_seconds,
            retry_attempts=retry_attempts,
            retry_backoff_seconds=retry_backoff_seconds,
            retry_enable_exponential_backoff=retry_enable_exponential_backoff,
            retryable_status_codes=retryable_status_codes,
            circuit_error_ratio=circuit_error_ratio,
            circuit_response_time=circuit_response_time,
            circuit_recovery_time=circuit_recovery_time,
            circuit_broken_time=circuit_broken_time,
        )
        notification_clients.append(fallback_client)

    notification_service = NotificationService(
        notification_clients=notification_clients
    )
    update_fetcher_service = LinkUpdateFetcherService(
        external_clients=[github_client, stackoverflow_client]
    )

    return UpdateProcessorWorkerContext(
        tracking_repository=repository,
        update_fetcher_service=update_fetcher_service,
        notification_service=notification_service,
    )


def make_update_processor_worker_context_factory(
    access_type: str,
    orm_url: str,
    raw_sql_url: str,
    github_base_url: str,
    stackoverflow_base_url: str,
    interservice_transport: str,
    bot_grpc_target: str,
    bot_http_url: str,
    kafka_bootstrap_servers: str,
    kafka_notification_topic: str,
    schema_registry_url: str,
    timeout_seconds: int,
    retry_attempts: int,
    retry_backoff_seconds: int,
    retry_enable_exponential_backoff: bool,
    retryable_status_codes: list[int],
    circuit_error_ratio: float,
    circuit_response_time: float,
    circuit_recovery_time: float,
    circuit_broken_time: float,
) -> Callable[..., Awaitable[UpdateProcessorWorkerContext]]:
    async def factory() -> UpdateProcessorWorkerContext:
        return await build_update_processor_worker_context(
            access_type=access_type,
            orm_url=orm_url,
            raw_sql_url=raw_sql_url,
            github_base_url=github_base_url,
            stackoverflow_base_url=stackoverflow_base_url,
            interservice_transport=interservice_transport,
            bot_grpc_target=bot_grpc_target,
            bot_http_url=bot_http_url,
            kafka_bootstrap_servers=kafka_bootstrap_servers,
            kafka_notification_topic=kafka_notification_topic,
            schema_registry_url=schema_registry_url,
            timeout_seconds=timeout_seconds,
            retry_attempts=retry_attempts,
            retry_backoff_seconds=retry_backoff_seconds,
            retry_enable_exponential_backoff=retry_enable_exponential_backoff,
            retryable_status_codes=retryable_status_codes,
            circuit_error_ratio=circuit_error_ratio,
            circuit_response_time=circuit_response_time,
            circuit_recovery_time=circuit_recovery_time,
            circuit_broken_time=circuit_broken_time,
        )

    return factory
