import asyncio
import structlog

from bot_service.application.common.runners.base_runner import BaseRunner
from bot_service.setup.app_lifecycle import ApplicationLifecycle
from bot_service.setup.ioc.metrics_server_runner_builder import (
    build_metrics_server_runner,
)
from setup.config.settings import settings
from setup.config.setup_logger import setup_logger
from application.services.tracking_service import TrackingService
from application.services.update_service import UpdateService
from infrastructure.adapters.telegram.handlers_provider import HandlersProvider
from infrastructure.adapters.telegram.telegram_client import TelegramClient
from infrastructure.adapters.redis.redis_notifications_delivered_storage import (
    RedisDeliveredNotificationsStorage,
)

from presentation.http.app_factory import create_app
from setup.ioc.notification_server_runner_builder import (
    build_notification_server_runner,
)
from setup.ioc.scrapper_client_builder import build_scrapper_client

setup_logger()
logger = structlog.get_logger(__name__)


async def main():
    logger.info("bot_starting", transport=settings.interservice_transport)

    scrapper_client = build_scrapper_client(
        interservice_transport=settings.interservice_transport,
        scrapper_url=str(settings.scrapper_url),
        scrapper_grpc_target=settings.scrapper_grpc_target,
        timeout_seconds=settings.timeout_seconds,
        retry_attempts=settings.retry_attempts,
        retry_backoff_seconds=settings.retry_backoff_seconds,
        retry_enable_exponential_backoff=settings.retry_enable_exponential_backoff,
        retryable_status_codes=settings.retryable_status_codes_list,
        circuit_error_ratio=settings.circuit_error_ratio,
        circuit_response_time=settings.circuit_response_time,
        circuit_recovery_time=settings.circuit_recovery_time,
        circuit_broken_time=settings.circuit_broken_time,
    )

    # впоследствии заменю hard code domain-ов на получение с помощью api
    validated_domains = ["github.com", "stackoverflow.com"]
    link_service = TrackingService(
        scrapper=scrapper_client,
        validated_domains=validated_domains,
    )
    handlers_provider = HandlersProvider(link_service)
    telegram_client = TelegramClient(settings.bot_token, handlers_provider)
    update_service = UpdateService(telegram_client)
    delivered_notifications_storage = RedisDeliveredNotificationsStorage(
        redis_url=settings.redis_url,
        ttl_seconds=settings.redis_delivered_notifications_ttl_seconds,
    )
    app = create_app(
        title="bot-service",
        version="1.0.0",
        contact_name="Kirill Kravchuk",
        contact_url="https://github.com",
        update_service=update_service,
        request_limit=settings.request_limit,
        request_limit_period=settings.request_limit_period,
    )

    server_runners: list[BaseRunner] = []
    main_server_runner = build_notification_server_runner(
        notification_transport=settings.notification_transport,
        bot_grpc_host=settings.bot_grpc_host,
        bot_grpc_port=settings.bot_grpc_port,
        http_bot_url=settings.bot_url,
        kafka_bootstrap_servers=settings.kafka_bootstrap_servers,
        kafka_notification_consumer_group=settings.kafka_notification_consumer_group,
        kafka_auto_offset_reset=settings.kafka_auto_offset_reset,
        kafka_enable_auto_commit=settings.kafka_enable_auto_commit,
        kafka_notification_topic=settings.kafka_notification_topic,
        kafka_notification_dlq_topic=settings.kafka_notification_dlq_topic,
        kafka_max_processing_retries=settings.kafka_max_processing_retries,
        update_service=update_service,
        delivered_notifications_storage=delivered_notifications_storage,
        app=app,
        schema_registry_url=settings.schema_registry_url,
    )
    server_runners.append(main_server_runner)

    if settings.notification_transport != "kafka":
        fallback_server_runner = build_notification_server_runner(
            notification_transport="kafka",
            bot_grpc_host=settings.bot_grpc_host,
            bot_grpc_port=settings.bot_grpc_port,
            http_bot_url=settings.bot_url,
            kafka_bootstrap_servers=settings.kafka_bootstrap_servers,
            kafka_notification_consumer_group=settings.kafka_notification_consumer_group,
            kafka_auto_offset_reset=settings.kafka_auto_offset_reset,
            kafka_enable_auto_commit=settings.kafka_enable_auto_commit,
            kafka_notification_topic=settings.kafka_notification_topic,
            kafka_notification_dlq_topic=settings.kafka_notification_dlq_topic,
            kafka_max_processing_retries=settings.kafka_max_processing_retries,
            update_service=update_service,
            delivered_notifications_storage=delivered_notifications_storage,
            app=app,
            schema_registry_url=settings.schema_registry_url,
        )
        server_runners.append(fallback_server_runner)

    metrics_server_runner = build_metrics_server_runner(
        host=settings.metrics_host,
        port=settings.metrics_port,
    )

    server_runners.append(metrics_server_runner)

    lifecycle = ApplicationLifecycle(
        telegram_client=telegram_client,
        server_runners=server_runners,
    )

    try:
        await lifecycle.run()

    except Exception as exc:
        logger.exception("scrapper_application_crashed", error=str(exc))
        raise

    finally:
        await scrapper_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
