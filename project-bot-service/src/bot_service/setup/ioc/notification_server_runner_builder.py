from fastapi import FastAPI
from pydantic import HttpUrl

from bot_service.application.ports.delivered_notifications_storage_port import (
    DeliveredNotificationsStoragePort,
)
from bot_service.presentation.grpc.grpc_server_factory import build_grpc_server
from bot_service.presentation.grpc.grpc_server_runner import GrpcServerRunner
from bot_service.presentation.http.http_server_factory import build_http_server
from bot_service.presentation.http.http_server_runner import HttpServerRunner
from bot_service.presentation.kafka.kafka_consumer_runner import KafkaConsumerRunner
from bot_service.presentation.kafka.kafka_notification_consumer import (
    KafkaNotificationConsumer,
)
from bot_service.application.common.runners.base_runner import BaseRunner
from bot_service.application.services.update_service import UpdateService


def build_notification_server_runner(
    notification_transport: str,
    bot_grpc_host: str,
    bot_grpc_port: int,
    http_bot_url: HttpUrl,
    kafka_bootstrap_servers: str,
    kafka_notification_consumer_group: str,
    kafka_auto_offset_reset: str,
    kafka_enable_auto_commit: bool,
    kafka_notification_topic: str,
    kafka_notification_dlq_topic: str,
    kafka_max_processing_retries: int,
    delivered_notifications_storage: DeliveredNotificationsStoragePort,
    update_service: UpdateService,
    app: FastAPI,
    schema_registry_url: str,
) -> BaseRunner:

    match notification_transport:
        case "grpc":
            grpc_server = build_grpc_server(
                update_service=update_service,
                host=bot_grpc_host,
                port=bot_grpc_port,
            )
            return GrpcServerRunner(grpc_server)
        case "http":
            http_server = build_http_server(
                app=app,
                host=http_bot_url.host,
                port=http_bot_url.port,
            )
            return HttpServerRunner(http_server)
        case "kafka":
            consumer = KafkaNotificationConsumer(
                bootstrap_servers=kafka_bootstrap_servers,
                group_id=kafka_notification_consumer_group,
                auto_offset_reset=kafka_auto_offset_reset,
                enable_auto_commit=kafka_enable_auto_commit,
                topic=kafka_notification_topic,
                dlq_topic=kafka_notification_dlq_topic,
                max_processing_retries=kafka_max_processing_retries,
                update_service=update_service,
                delivered_notifications_storage=delivered_notifications_storage,
                schema_registry_url=schema_registry_url,
            )

            return KafkaConsumerRunner(consumer)
        case _:
            raise ValueError(
                f"Такого транспорта не существует: {notification_transport}"
            )
